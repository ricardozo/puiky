import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type Task } from '../api'
import { TaskEditor } from './Board'

const colorEstado: Record<string, string> = {
  planeada: 'bg-slate-700 text-slate-300',
  en_ejecucion: 'bg-indigo-600/30 text-indigo-300',
  en_pausa: 'bg-amber-600/30 text-amber-300',
  terminada: 'bg-emerald-600/30 text-emerald-300',
}

function vencimiento(t: Task): { texto: string; clase: string } {
  if (!t.fecha_limite) return { texto: 'sin fecha', clase: 'text-slate-600' }
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  const venc = new Date(t.fecha_limite + 'T00:00')
  const dias = Math.round((venc.getTime() - hoy.getTime()) / 86400000)
  const fecha = venc.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })
  if (t.estado === 'terminada') return { texto: fecha, clase: 'text-slate-500' }
  if (dias < 0) return { texto: `${fecha} · vencida`, clase: 'text-red-400' }
  if (dias === 0) return { texto: `${fecha} · hoy`, clase: 'text-red-300' }
  if (dias <= 3) return { texto: `${fecha} · en ${dias}d`, clase: 'text-amber-300' }
  return { texto: fecha, clase: 'text-slate-400' }
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
      <h2 className="text-xl font-semibold">Tareas</h2>

      <form onSubmit={buscar} className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar tarea por título…"
          className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 outline-none focus:border-indigo-500"
        />
        <button className="rounded-lg border border-slate-700 px-4 hover:bg-slate-800">
          Buscar
        </button>
        {q && (
          <button
            type="button"
            onClick={() => {
              setQ('')
              cargar()
            }}
            className="rounded-lg border border-slate-700 px-4 hover:bg-slate-800"
          >
            Limpiar
          </button>
        )}
      </form>

      <p className="text-xs text-slate-500">
        Ordenadas por fecha de vencimiento (las sin fecha, al final).
      </p>

      {cargando ? (
        <p className="text-slate-500">Cargando…</p>
      ) : tasks.length === 0 ? (
        <p className="text-slate-500">Sin tareas.</p>
      ) : (
        <ul className="divide-y divide-slate-800 rounded-xl border border-slate-800">
          {tasks.map((t) => {
            const v = vencimiento(t)
            return (
              <li key={t.id}>
                <button
                  onClick={() => setAbierta(t)}
                  className="w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-slate-800/40 transition"
                >
                  <span
                    className={`shrink-0 rounded px-2 py-0.5 text-xs ${
                      colorEstado[t.estado] ?? 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {t.estado}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div
                      className={
                        t.estado === 'terminada'
                          ? 'line-through text-slate-500'
                          : ''
                      }
                    >
                      {t.titulo}
                    </div>
                    <div className="text-xs text-slate-500">
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
