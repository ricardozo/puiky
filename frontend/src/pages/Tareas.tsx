import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type Task } from '../api'
import { TaskEditor } from './Board'

const colorEstado: Record<string, string> = {
  planeada: 'pill-mute',
  en_ejecucion: 'pill-active',
  en_pausa: 'pill-warn',
  terminada: 'pill-ok',
}

function vencimiento(t: Task): { texto: string; clase: string } {
  if (!t.fecha_limite) return { texto: 'sin fecha', clase: 'text-faint' }
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  const venc = new Date(t.fecha_limite + 'T00:00')
  const dias = Math.round((venc.getTime() - hoy.getTime()) / 86400000)
  const fecha = venc.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
  if (t.estado === 'terminada') return { texto: fecha, clase: 'text-faint' }
  if (dias < 0)
    return { texto: `${fecha} · vencida`, clase: 'text-[color:var(--c-danger)]' }
  if (dias === 0)
    return { texto: `${fecha} · hoy`, clase: 'text-[color:var(--c-danger)]' }
  if (dias <= 3)
    return { texto: `${fecha} · en ${dias}d`, clase: 'text-brand' }
  return { texto: fecha, clase: 'text-muted' }
}

export default function Tareas() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [q, setQ] = useState('')
  const [cargando, setCargando] = useState(true)
  const [abierta, setAbierta] = useState<Task | null>(null)

  const cargar = useCallback(
    (texto?: string) =>
      api
        .listTasks(texto)
        .then(setTasks)
        .finally(() => setCargando(false)),
    []
  )

  useEffect(() => {
    cargar()
  }, [cargar])

  const buscar = (e: FormEvent) => {
    e.preventDefault()
    cargar(q.trim() || undefined)
  }

  return (
    <div className="space-y-5 max-w-3xl">
      <h2 className="font-serif text-2xl">Tareas</h2>

      <form onSubmit={buscar} className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar tarea por título…"
          className="input flex-1"
        />
        <button className="btn-ghost btn">Buscar</button>
        {q && (
          <button
            type="button"
            onClick={() => {
              setQ('')
              cargar()
            }}
            className="btn-ghost btn"
          >
            Limpiar
          </button>
        )}
      </form>

      <p className="text-xs text-faint">
        Ordenadas por fecha de vencimiento (las sin fecha, al final).
      </p>

      {cargando ? (
        <p className="text-faint">Cargando…</p>
      ) : tasks.length === 0 ? (
        <p className="text-faint">Sin tareas.</p>
      ) : (
        <ul className="card divide-y divide-[color:var(--c-line)] p-0 overflow-hidden">
          {tasks.map((t) => {
            const v = vencimiento(t)
            return (
              <li key={t.id}>
                <button
                  onClick={() => setAbierta(t)}
                  className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-surface-2 transition"
                >
                  <span className={`pill shrink-0 ${colorEstado[t.estado] ?? 'pill-mute'}`}>
                    {t.estado}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div
                      className={
                        t.estado === 'terminada' ? 'line-through text-faint' : ''
                      }
                    >
                      {t.titulo}
                    </div>
                    <div className="text-xs text-muted">
                      {t.proyecto ? `📋 ${t.proyecto}` : 'sin proyecto'}
                      {t.checklist.length > 0 &&
                        ` · ☑ ${t.checklist.filter((i) => i.hecho).length}/${t.checklist.length}`}
                    </div>
                  </div>
                  <span className={`shrink-0 text-xs ${v.clase}`}>{v.texto}</span>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {abierta && (
        <TaskEditor
          taskInicial={abierta}
          onClose={() => {
            setAbierta(null)
            cargar(q.trim() || undefined)
          }}
        />
      )}
    </div>
  )
}
