import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Project, type Task, type TimeEntry } from '../api'
import { TaskEditor } from './Board'
import { fmtCrono, pomoMin } from '../tiempo'

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
  const [actual, setActual] = useState<TimeEntry | null>(null)
  const [ahora, setAhora] = useState(Date.now())
  const [vista, setVista] = useState<'proyecto' | 'foco'>(() => {
    try {
      return localStorage.getItem('puiky_tareas_vista') === 'foco' ? 'foco' : 'proyecto'
    } catch {
      return 'proyecto'
    }
  })
  const cambiarVista = (v: 'proyecto' | 'foco') => {
    setVista(v)
    try {
      localStorage.setItem('puiky_tareas_vista', v)
    } catch {
      // sin almacenamiento: la vista vale solo para esta visita
    }
  }

  const cargar = useCallback(async () => {
    const [ts, ps, cur] = await Promise.all([
      api.listTasks(),
      api.listProjects(),
      api.timeCurrent(),
    ])
    setTasks(ts)
    setProjects(ps)
    setActual(cur)
    setCargando(false)
  }, [])

  // Tic del cronómetro mientras haya sesión corriendo.
  useEffect(() => {
    if (!actual) return
    const t = setInterval(() => setAhora(Date.now()), 1000)
    return () => clearInterval(t)
  }, [actual])

  const transcurrido = actual
    ? Math.max(0, (ahora - new Date(actual.inicio).getTime()) / 1000)
    : 0

  // ▶ en otra tarea cierra la anterior (lo hace el servidor); ⏹ en la que
  // corre la para. Cronometrar nunca completa la tarea.
  const alternarTiempo = async (t: Task) => {
    if (actual?.task_id === t.id) {
      await api.timeStop()
      setActual(null)
    } else {
      setActual(await api.timeStart(t.id, pomoMin()))
      setAhora(Date.now())
    }
  }

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

  // ⭐ Foco del día: la marca guarda la fecha de hoy; mañana ya no cuenta.
  const alternarFoco = async (t: Task) => {
    const valor = t.foco_fecha === hoy ? null : hoy
    setTasks((prev) => prev.map((x) => (x.id === t.id ? { ...x, foco_fecha: valor } : x)))
    await api.updateTask(t.id, { foco_fecha: valor })
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
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-line overflow-hidden text-sm">
            {(
              [
                ['proyecto', '📁 Por proyecto'],
                ['foco', '🎯 Foco'],
              ] as const
            ).map(([v, label]) => (
              <button
                key={v}
                onClick={() => cambiarVista(v)}
                className={`px-3 py-1.5 transition ${
                  vista === v
                    ? 'bg-[var(--c-brand-soft)] text-brand font-medium'
                    : 'text-muted hover:text-ink'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <input
            value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
            placeholder="Filtrar…"
            className="input w-40 py-1.5 text-sm"
          />
        </div>
      </div>

      {actual && (
        <div
          className="card px-4 py-3 flex items-center justify-between gap-3"
          style={{
            borderColor: 'color-mix(in srgb, var(--c-teal) 60%, var(--c-line))',
          }}
        >
          <div className="min-w-0 text-sm">
            <span className="text-muted">⏱ Trabajando en </span>
            <span className="font-medium">{actual.tarea}</span>
            {actual.proyecto && (
              <span className="text-faint"> · {actual.proyecto}</span>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="font-serif text-xl tabular-nums">
              {fmtCrono(transcurrido)}
            </span>
            <button
              onClick={async () => {
                await api.timeStop()
                setActual(null)
              }}
              className="btn text-sm py-1"
            >
              ⏹ Parar
            </button>
          </div>
        </div>
      )}

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

      {vista === 'foco' && (
        <VistaFoco
          tareas={tasks.filter(
            (t) =>
              t.estado !== 'terminada' &&
              (!filtro || t.titulo.toLowerCase().includes(filtro.toLowerCase()))
          )}
          hoy={hoy}
          fila={(t) => (
            <FilaTarea
              key={t.id}
              t={t}
              hoy={hoy}
              hecha={hechasAhora.has(t.id)}
              conProyecto
              corriendo={actual?.task_id === t.id}
              transcurrido={transcurrido}
              onCompletar={completar}
              onReabrir={reabrir}
              onAbrir={setAbierta}
              onTiempo={alternarTiempo}
              onFoco={alternarFoco}
            />
          )}
        />
      )}

      {vista === 'proyecto' && grupos.map(({ proyecto, tareas }) => (
        <TarjetaProyecto
          key={proyecto.id}
          proyecto={proyecto}
          tareas={tareas}
          hechasAhora={hechasAhora}
          onCompletar={completar}
          onReabrir={reabrir}
          onAbrir={setAbierta}
          corriendoId={actual?.task_id ?? null}
          transcurrido={transcurrido}
          onTiempo={alternarTiempo}
          onFoco={alternarFoco}
          hoy={hoy}
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
  corriendoId,
  transcurrido,
  onTiempo,
  onFoco,
  hoy,
  onCrear,
  onVerTablero,
}: {
  proyecto: Project
  tareas: Task[]
  hechasAhora: Set<string>
  onCompletar: (t: Task) => void
  onReabrir: (t: Task) => void
  onAbrir: (t: Task) => void
  corriendoId: string | null
  transcurrido: number
  onTiempo: (t: Task) => void
  onFoco: (t: Task) => void
  hoy: string
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
          {tareas.map((t) => (
            <FilaTarea
              key={t.id}
              t={t}
              hoy={hoy}
              hecha={t.estado === 'terminada' || hechasAhora.has(t.id)}
              corriendo={corriendoId === t.id}
              transcurrido={transcurrido}
              onCompletar={onCompletar}
              onReabrir={onReabrir}
              onAbrir={onAbrir}
              onTiempo={onTiempo}
              onFoco={onFoco}
            />
          ))}
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

const PRIORIDAD: Record<string, { label: string; clase: string }> = {
  alta: { label: 'alta', clase: 'text-[color:var(--c-danger)]' },
  media: { label: 'media', clase: 'text-brand' },
  baja: { label: 'baja', clase: 'text-faint' },
}

function FilaTarea({
  t,
  hoy,
  hecha,
  conProyecto = false,
  corriendo,
  transcurrido,
  onCompletar,
  onReabrir,
  onAbrir,
  onTiempo,
  onFoco,
}: {
  t: Task
  hoy: string
  hecha: boolean
  conProyecto?: boolean
  corriendo: boolean
  transcurrido: number
  onCompletar: (t: Task) => void
  onReabrir: (t: Task) => void
  onAbrir: (t: Task) => void
  onTiempo: (t: Task) => void
  onFoco: (t: Task) => void
}) {
  const v = vencimiento(t)
  const enFoco = t.foco_fecha === hoy
  const prio = t.prioridad ? PRIORIDAD[t.prioridad] : null
  return (
    <li
      className="flex items-center gap-3 px-4 py-2.5"
      style={
        corriendo
          ? { background: 'color-mix(in srgb, var(--c-teal) 12%, transparent)' }
          : undefined
      }
    >
      <input
        type="checkbox"
        checked={hecha}
        onChange={() => (hecha ? onReabrir(t) : onCompletar(t))}
        className="size-4 accent-[color:var(--c-teal)] shrink-0 cursor-pointer"
        title={hecha ? 'Reabrir' : 'Marcar completada'}
      />
      <button onClick={() => onAbrir(t)} className="min-w-0 flex-1 text-left">
        <span className={hecha ? 'line-through text-faint' : ''}>
          {t.recurrencia && <span title={`Recurrente: ${t.recurrencia}`}>🔁 </span>}
          {t.titulo}
        </span>
        {conProyecto && t.proyecto && (
          <span className="text-xs text-faint ml-2">· {t.proyecto}</span>
        )}
        {prio && !hecha && (
          <span className={`text-xs ml-2 ${prio.clase}`} title="Prioridad">
            ● {prio.label}
          </span>
        )}
        {t.checklist.length > 0 && (
          <span className="text-xs text-muted ml-2">
            ☑ {t.checklist.filter((i) => i.hecho).length}/{t.checklist.length}
          </span>
        )}
      </button>
      {!hecha && v.texto && (
        <span className={`shrink-0 text-xs ${v.clase}`}>{v.texto}</span>
      )}
      {!hecha && (
        <button
          onClick={() => onFoco(t)}
          title={enFoco ? 'Quitar del foco de hoy' : 'Poner en el foco de hoy'}
          className={`shrink-0 transition ${
            enFoco ? 'text-brand' : 'text-faint hover:text-brand'
          }`}
        >
          {enFoco ? '★' : '☆'}
        </button>
      )}
      {!hecha && (
        <button
          onClick={() => onTiempo(t)}
          title={corriendo ? 'Parar el tiempo' : 'Iniciar tiempo en esta tarea'}
          className={`shrink-0 rounded-lg border px-2 py-0.5 text-xs tabular-nums transition ${
            corriendo
              ? 'border-[color:var(--c-teal)] text-ink'
              : 'border-line text-faint hover:text-ink hover:border-[color:var(--c-teal)]'
          }`}
        >
          {corriendo ? `⏹ ${fmtCrono(transcurrido)}` : '▶'}
        </button>
      )}
    </li>
  )
}

function Seccion({
  titulo,
  ayuda,
  items,
  fila,
}: {
  titulo: string
  ayuda?: string
  items: Task[]
  fila: (t: Task) => ReactNode
}) {
  return (
    <section className="card p-0 overflow-hidden">
      <div className="px-4 py-2.5 border-b border-line flex items-baseline justify-between gap-2">
        <h3 className="font-medium">{titulo}</h3>
        <span className="text-xs text-muted">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-faint text-sm px-4 py-3">{ayuda ?? 'Nada aquí.'}</p>
      ) : (
        <ul className="divide-y divide-[color:var(--c-line)]">{items.map(fila)}</ul>
      )}
    </section>
  )
}

// Vista 🎯 Foco: qué hacer ahora, mezclando proyectos. Cada tarea aparece en
// una sola sección, la primera que le aplique.
function VistaFoco({
  tareas,
  hoy,
  fila,
}: {
  tareas: Task[]
  hoy: string
  fila: (t: Task) => ReactNode
}) {
  const porFecha = (a: Task, b: Task) =>
    (a.fecha_limite ?? '9999-12-31').localeCompare(b.fecha_limite ?? '9999-12-31')
  const peso = (t: Task) => (t.prioridad === 'alta' ? 0 : t.prioridad === 'media' ? 1 : 2)
  const diasHasta = (f: string) =>
    Math.round(
      (new Date(f + 'T00:00').getTime() - new Date(hoy + 'T00:00').getTime()) / 86400000
    )

  const foco = tareas.filter((t) => t.foco_fecha === hoy).sort((a, b) => peso(a) - peso(b))
  const fueraFoco = tareas.filter((t) => t.foco_fecha !== hoy)
  const urgentes = fueraFoco
    .filter((t) => t.fecha_limite && t.fecha_limite <= hoy)
    .sort(porFecha)
  const resto = fueraFoco.filter((t) => !(t.fecha_limite && t.fecha_limite <= hoy))
  const importantes = resto.filter((t) => t.prioridad === 'alta').sort(porFecha)
  const proximas = resto
    .filter((t) => t.prioridad !== 'alta' && t.fecha_limite && diasHasta(t.fecha_limite) <= 3)
    .sort(porFecha)

  return (
    <>
      <Seccion
        titulo="⭐ Foco de hoy"
        ayuda="Marca con ☆ las 3–5 tareas que decides hacer hoy. Mañana arrancas limpio."
        items={foco}
        fila={fila}
      />
      <Seccion titulo="⏰ Vencidas y para hoy" items={urgentes} ayuda="Nada vencido 🎉" fila={fila} />
      <Seccion
        titulo="🔥 Prioridad alta"
        items={importantes}
        ayuda="Sin tareas de prioridad alta. Asígnala abriendo la tarea."
        fila={fila}
      />
      {proximas.length > 0 && (
        <Seccion titulo="📅 Próximos 3 días" items={proximas} fila={fila} />
      )}
    </>
  )
}
