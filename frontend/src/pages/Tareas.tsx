import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Project, type Task } from '../api'
import { TaskEditor } from './Board'

function hoyISO(): string {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function vencimiento(t: Task): { texto: string; clase: string } {
  if (!t.fecha_limite) return { texto: '', clase: 'text-faint' }
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  const venc = new Date(t.fecha_limite + 'T00:00')
  const dias = Math.round((venc.getTime() - hoy.getTime()) / 86400000)
  const fecha = venc.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
  if (dias < 0)
    return { texto: `⏰ ${fecha} · vencida`, clase: 'text-[color:var(--c-danger)]' }
  if (dias === 0) return { texto: 'hoy', clase: 'text-[color:var(--c-danger)]' }
  if (dias === 1) return { texto: 'mañana', clase: 'text-brand' }
  if (dias <= 3) return { texto: `${fecha} · en ${dias}d`, clase: 'text-brand' }
  return { texto: fecha, clase: 'text-muted' }
}

type Grupo = { proyecto: Project; tareas: Task[] }

export default function Tareas() {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<Task[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [cargando, setCargando] = useState(true)
  const [abierta, setAbierta] = useState<Task | null>(null)
  const [nueva, setNueva] = useState('')
  const [hechasAhora, setHechasAhora] = useState<Set<string>>(new Set())
  const [aviso, setAviso] = useState('')
  const [filtro, setFiltro] = useState('')

  const cargar = useCallback(async () => {
    const [ts, ps] = await Promise.all([api.listTasks(), api.listProjects()])
    setTasks(ts)
    setProjects(ps)
    setCargando(false)
  }, [])

  useEffect(() => {
    cargar()
  }, [cargar])

  const hoy = hoyISO()
  const personal = projects.find((p) => p.es_personal)

  // Agrupa: activas (o chequeadas en esta sesión) por proyecto. Personal
  // primero; el resto por urgencia (su tarea más vencida/cercana).
  const grupos = useMemo<Grupo[]>(() => {
    const visibles = tasks.filter(
      (t) =>
        (t.estado !== 'terminada' || hechasAhora.has(t.id)) &&
        (!filtro || t.titulo.toLowerCase().includes(filtro.toLowerCase()))
    )
    const porProyecto = new Map<string, Task[]>()
    for (const t of visibles) {
      const key = t.project_id ?? 'sin'
      porProyecto.set(key, [...(porProyecto.get(key) ?? []), t])
    }
    const orden = (t: Task) => (t.fecha_limite ? t.fecha_limite : '9999-12-31')
    const urgencia = (ts: Task[]) =>
      ts.reduce((min, t) => (orden(t) < min ? orden(t) : min), '9999-12-31')

    const out: Grupo[] = []
    for (const p of projects) {
      const ts = porProyecto.get(p.id)
      if (!ts && !p.es_personal) continue
      out.push({
        proyecto: p,
        tareas: (ts ?? []).sort((a, b) => orden(a).localeCompare(orden(b))),
      })
    }
    out.sort((a, b) => {
      if (a.proyecto.es_personal !== b.proyecto.es_personal)
        return a.proyecto.es_personal ? -1 : 1
      return urgencia(a.tareas).localeCompare(urgencia(b.tareas))
    })
    return out
  }, [tasks, projects, hechasAhora, filtro])

  const activas = tasks.filter((t) => t.estado !== 'terminada')
  const vencidas = activas.filter((t) => t.fecha_limite && t.fecha_limite < hoy)
  const paraHoy = activas.filter((t) => t.fecha_limite === hoy)

  const completar = async (t: Task) => {
    const r = await api.completeTask(t.id)
    if (t.recurrencia && r.estado !== 'terminada') {
      // Recurrente: se recicló; avisa cuándo vuelve.
      const f = r.fecha_limite
        ? new Date(r.fecha_limite + 'T00:00').toLocaleDateString('es-CO', {
            day: 'numeric',
            month: 'long',
          })
        : 'el siguiente periodo'
      setAviso(`🔁 «${t.titulo}» hecha — vuelve el ${f}.`)
    } else {
      setHechasAhora((prev) => new Set(prev).add(t.id))
    }
    cargar()
  }

  const reabrir = async (t: Task) => {
    await api.updateTask(t.id, { estado: 'en_ejecucion' })
    setHechasAhora((prev) => {
      const s = new Set(prev)
      s.delete(t.id)
      return s
    })
    cargar()
  }

  const crearPersonal = async (e: FormEvent) => {
    e.preventDefault()
    if (!nueva.trim()) return
    // Sin project_id: el backend la manda al proyecto Personal.
    await api.createTask(nueva.trim(), personal?.id)
    setNueva('')
    cargar()
  }

  if (cargando) return <p className="text-faint">Cargando…</p>

  return (
    <div className="space-y-5 max-w-3xl">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="font-serif text-2xl">Tareas</h2>
          <p className="text-sm mt-1">
            {vencidas.length > 0 && (
              <span className="text-[color:var(--c-danger)]">
                {vencidas.length} vencida{vencidas.length === 1 ? '' : 's'}
              </span>
            )}
            {vencidas.length > 0 && paraHoy.length > 0 && (
              <span className="text-faint"> · </span>
            )}
            {paraHoy.length > 0 && (
              <span className="text-brand">
                {paraHoy.length} para hoy
              </span>
            )}
            {vencidas.length === 0 && paraHoy.length === 0 && (
              <span className="text-faint">Nada vence hoy 🎉</span>
            )}
          </p>
        </div>
        <input
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          placeholder="Filtrar…"
          className="input w-40 py-1.5 text-sm"
        />
      </div>

      <form onSubmit={crearPersonal} className="flex gap-2">
        <input
          value={nueva}
          onChange={(e) => setNueva(e.target.value)}
          placeholder="Nueva tarea personal…"
          className="input flex-1"
        />
        <button className="btn">+ Crear</button>
      </form>

      {aviso && (
        <p className="text-sm text-[color:var(--c-green)]">{aviso}</p>
      )}

      {grupos.map(({ proyecto, tareas }) => (
        <TarjetaProyecto
          key={proyecto.id}
          proyecto={proyecto}
          tareas={tareas}
          hechasAhora={hechasAhora}
          onCompletar={completar}
          onReabrir={reabrir}
          onAbrir={setAbierta}
          onCrear={async (titulo) => {
            await api.createTask(titulo, proyecto.id)
            cargar()
          }}
          onVerTablero={() => navigate(`/proyectos/${proyecto.id}`)}
        />
      ))}

      {abierta && (
        <TaskEditor
          taskInicial={abierta}
          onClose={() => {
            setAbierta(null)
            cargar()
          }}
        />
      )}
    </div>
  )
}

function TarjetaProyecto({
  proyecto,
  tareas,
  hechasAhora,
  onCompletar,
  onReabrir,
  onAbrir,
  onCrear,
  onVerTablero,
}: {
  proyecto: Project
  tareas: Task[]
  hechasAhora: Set<string>
  onCompletar: (t: Task) => void
  onReabrir: (t: Task) => void
  onAbrir: (t: Task) => void
  onCrear: (titulo: string) => Promise<void>
  onVerTablero: () => void
}) {
  const [nueva, setNueva] = useState('')

  const crear = async (e: FormEvent) => {
    e.preventDefault()
    if (!nueva.trim()) return
    await onCrear(nueva.trim())
    setNueva('')
  }

  return (
    <section className="card p-0 overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-line">
        <button
          onClick={onVerTablero}
          className="flex items-center gap-2 font-medium hover:text-brand transition"
          title="Ver tablero"
        >
          <span>{proyecto.es_personal ? '🏠' : '💼'}</span>
          {proyecto.nombre}
        </button>
        <span className="text-xs text-muted">
          {proyecto.total_tareas > 0 &&
            `${proyecto.tareas_terminadas}/${proyecto.total_tareas}`}
          {proyecto.avance !== null && ` · ${proyecto.avance}%`}
        </span>
      </div>

      {tareas.length === 0 ? (
        <p className="text-faint text-sm px-4 py-3">Sin tareas activas.</p>
      ) : (
        <ul className="divide-y divide-[color:var(--c-line)]">
          {tareas.map((t) => {
            const hecha = t.estado === 'terminada' || hechasAhora.has(t.id)
            const v = vencimiento(t)
            return (
              <li key={t.id} className="flex items-center gap-3 px-4 py-2.5">
                <input
                  type="checkbox"
                  checked={hecha}
                  onChange={() => (hecha ? onReabrir(t) : onCompletar(t))}
                  className="size-4 accent-[color:var(--c-teal)] shrink-0 cursor-pointer"
                  title={hecha ? 'Reabrir' : 'Marcar completada'}
                />
                <button
                  onClick={() => onAbrir(t)}
                  className="min-w-0 flex-1 text-left"
                >
                  <span className={hecha ? 'line-through text-faint' : ''}>
                    {t.recurrencia && (
                      <span title={`Recurrente: ${t.recurrencia}`}>🔁 </span>
                    )}
                    {t.titulo}
                  </span>
                  {t.checklist.length > 0 && (
                    <span className="text-xs text-muted ml-2">
                      ☑ {t.checklist.filter((i) => i.hecho).length}/
                      {t.checklist.length}
                    </span>
                  )}
                </button>
                {!hecha && v.texto && (
                  <span className={`shrink-0 text-xs ${v.clase}`}>{v.texto}</span>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {!proyecto.es_personal && (
        <form onSubmit={crear} className="border-t border-line">
          <input
            value={nueva}
            onChange={(e) => setNueva(e.target.value)}
            placeholder="+ agregar tarea…"
            className="w-full bg-transparent px-4 py-2 text-sm outline-none placeholder:text-faint"
          />
        </form>
      )}
    </section>
  )
}
