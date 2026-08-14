import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError, type Task, type TimeEntry } from '../api'

// Preferencia local del largo del pomodoro (minutos).
const POMO_KEY = 'puiky_pomodoro_min'
const pomoGuardado = () => {
  const v = Number(localStorage.getItem(POMO_KEY))
  return v >= 5 && v <= 240 ? v : 45
}

const p2 = (n: number) => String(n).padStart(2, '0')

function fmtDur(seg: number): string {
  const h = Math.floor(seg / 3600)
  const m = Math.floor((seg % 3600) / 60)
  if (h > 0) return `${h}h ${p2(m)}m`
  return `${m}m`
}

function fmtCrono(seg: number): string {
  const h = Math.floor(seg / 3600)
  const m = Math.floor((seg % 3600) / 60)
  const s = Math.floor(seg % 60)
  return h > 0 ? `${h}:${p2(m)}:${p2(s)}` : `${m}:${p2(s)}`
}

const hora = (iso: string) =>
  new Date(iso).toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' })

// ISO -> valor de input datetime-local en hora local.
function aLocalInput(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}T${p2(d.getHours())}:${p2(d.getMinutes())}`
}
const aISO = (local: string) => new Date(local).toISOString()

// Bip suave con WebAudio (sin archivos): tres tonos cortos.
function bip() {
  try {
    const ctx = new AudioContext()
    ;[0, 0.35, 0.7].forEach((t, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.frequency.value = i === 2 ? 880 : 660
      gain.gain.setValueAtTime(0.001, ctx.currentTime + t)
      gain.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + t + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.3)
      osc.connect(gain).connect(ctx.destination)
      osc.start(ctx.currentTime + t)
      osc.stop(ctx.currentTime + t + 0.32)
    })
  } catch {
    // sin audio disponible: el color ya avisa
  }
}

export default function Tiempo() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [entries, setEntries] = useState<TimeEntry[]>([])
  const [actual, setActual] = useState<TimeEntry | null>(null)
  const [pomoMin, setPomoMin] = useState(pomoGuardado)
  const [ahora, setAhora] = useState(Date.now())
  const [editando, setEditando] = useState<TimeEntry | null>(null)
  const [otraTarea, setOtraTarea] = useState('')
  const [error, setError] = useState('')
  const avisado = useRef(false)

  const cargar = useCallback(() => {
    api.timeCurrent().then(setActual)
    api.listTimeEntries().then(setEntries)
  }, [])

  useEffect(() => {
    api.listTasks().then(setTasks)
    cargar()
  }, [cargar])

  // Tic del cronómetro (cada segundo mientras haya sesión).
  useEffect(() => {
    if (!actual) return
    const t = setInterval(() => setAhora(Date.now()), 1000)
    return () => clearInterval(t)
  }, [actual])

  const transcurrido = actual
    ? Math.max(0, (ahora - new Date(actual.inicio).getTime()) / 1000)
    : 0
  const pomoListo = actual !== null && transcurrido >= pomoMin * 60

  // Suena una sola vez por sesión al cumplir el pomodoro.
  useEffect(() => {
    if (pomoListo && !avisado.current) {
      avisado.current = true
      bip()
    }
    if (!pomoListo) avisado.current = false
  }, [pomoListo])

  const activas = useMemo(
    () => tasks.filter((t) => t.estado !== 'terminada'),
    [tasks]
  )
  // Tiles: las de Vida primero, luego las usadas hoy; el resto va al selector.
  const tiles = useMemo(() => {
    const usadasHoy = new Set(entries.map((e) => e.task_id))
    const vida = activas.filter((t) => t.proyecto?.toLowerCase() === 'vida')
    const otras = activas.filter(
      (t) => t.proyecto?.toLowerCase() !== 'vida' && usadasHoy.has(t.id)
    )
    return [...vida, ...otras]
  }, [activas, entries])

  const iniciar = async (taskId: string) => {
    setError('')
    try {
      await api.timeStart(taskId)
      avisado.current = false
      cargar()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo iniciar')
    }
  }

  const parar = async () => {
    await api.timeStop()
    cargar()
  }

  const guardarPomo = (v: number) => {
    setPomoMin(v)
    localStorage.setItem(POMO_KEY, String(v))
  }

  // Totales de hoy por tarea (las sesiones corriendo cuentan hasta ahora).
  const totales = useMemo(() => {
    const porTarea = new Map<string, { etiqueta: string; seg: number }>()
    let total = 0
    for (const e of entries) {
      const fin = e.fin ? new Date(e.fin).getTime() : ahora
      const seg = Math.max(0, (fin - new Date(e.inicio).getTime()) / 1000)
      total += seg
      const etiqueta = e.tarea ?? '(tarea eliminada)'
      const prev = porTarea.get(e.task_id)
      porTarea.set(e.task_id, { etiqueta, seg: (prev?.seg ?? 0) + seg })
    }
    const filas = [...porTarea.values()].sort((a, b) => b.seg - a.seg)
    return { total, filas }
  }, [entries, ahora])

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="font-serif text-2xl">Tiempo</h2>
        <label className="text-sm text-muted flex items-center gap-2">
          Pomodoro
          <input
            type="number"
            value={pomoMin}
            min={5}
            max={240}
            onChange={(e) => guardarPomo(Number(e.target.value) || 45)}
            className="input w-20 py-1"
          />
          min
        </label>
      </div>

      {/* Sesión corriendo */}
      {actual && (
        <div
          className="card p-5 flex items-center justify-between gap-4 flex-wrap"
          style={{
            borderColor: pomoListo
              ? 'var(--c-brand)'
              : 'color-mix(in srgb, var(--c-teal) 60%, var(--c-line))',
            background: pomoListo ? 'var(--c-brand-soft)' : undefined,
          }}
        >
          <div className="min-w-0">
            <p className="text-sm text-muted">
              {pomoListo ? '🍅 ¡Pomodoro cumplido! Hora de una pausa.' : 'Trabajando en'}
            </p>
            <p className="font-medium text-lg truncate">
              {actual.tarea}
              {actual.proyecto && (
                <span className="text-faint text-sm"> · {actual.proyecto}</span>
              )}
            </p>
            <p className="text-xs text-faint mt-0.5">desde las {hora(actual.inicio)}</p>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <span
              className="font-serif text-3xl tabular-nums"
              style={pomoListo ? { color: 'var(--c-brand)' } : undefined}
            >
              {fmtCrono(transcurrido)}
            </span>
            <button onClick={parar} className="btn">
              ⏹ Parar
            </button>
          </div>
        </div>
      )}

      {/* Tiles para arrancar */}
      <div className="space-y-2">
        <h3 className="eyebrow">¿En qué estás?</h3>
        <p className="text-xs text-faint">
          Toca para arrancar el conteo; empezar otra cosa cierra la anterior.
        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          {tiles.map((t) => {
            const activa = actual?.task_id === t.id
            return (
              <button
                key={t.id}
                onClick={() => (activa ? parar() : iniciar(t.id))}
                className="card text-left p-4 hover:border-teal transition"
                style={
                  activa
                    ? {
                        borderColor: pomoListo ? 'var(--c-brand)' : 'var(--c-teal)',
                        background: pomoListo ? 'var(--c-brand-soft)' : undefined,
                      }
                    : undefined
                }
              >
                <div className="font-medium">
                  {activa && (pomoListo ? '🍅 ' : '▶ ')}
                  {t.titulo}
                </div>
                <div className="text-xs text-faint mt-1">
                  {t.proyecto ?? 'sin proyecto'}
                  {activa && ` · ${fmtCrono(transcurrido)}`}
                </div>
              </button>
            )
          })}
        </div>
        <select
          value={otraTarea}
          onChange={(e) => {
            if (e.target.value) iniciar(e.target.value)
            setOtraTarea('')
          }}
          className="input w-auto text-sm"
        >
          <option value="">▶ Otra tarea…</option>
          {activas
            .filter((t) => !tiles.some((x) => x.id === t.id))
            .map((t) => (
              <option key={t.id} value={t.id}>
                {t.titulo}
                {t.proyecto ? ` · ${t.proyecto}` : ''}
              </option>
            ))}
        </select>
      </div>
      {error && <p className="text-[color:var(--c-danger)] text-sm">{error}</p>}

      {/* Resumen y sesiones de hoy */}
      {entries.length > 0 && (
        <>
          <section className="card p-4 space-y-2">
            <div className="flex items-baseline justify-between">
              <h3 className="eyebrow">Hoy</h3>
              <span className="font-serif text-xl">{fmtDur(totales.total)}</span>
            </div>
            {totales.filas.map((f) => (
              <div
                key={f.etiqueta}
                className="flex items-center justify-between text-sm border-t border-line pt-1.5"
              >
                <span className="text-muted truncate">{f.etiqueta}</span>
                <span className="tabular-nums shrink-0">{fmtDur(f.seg)}</span>
              </div>
            ))}
          </section>

          <div className="space-y-2">
            <h3 className="eyebrow">Sesiones de hoy</h3>
            <ul className="space-y-2">
              {entries.map((e) => (
                <li
                  key={e.id}
                  className="group card px-4 py-2.5 flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <p className="truncate">
                      {e.tarea}
                      {e.proyecto && (
                        <span className="text-faint text-sm"> · {e.proyecto}</span>
                      )}
                    </p>
                    <p className="text-xs text-faint mt-0.5">
                      {hora(e.inicio)} — {e.fin ? hora(e.fin) : 'corriendo'}
                      {e.fin &&
                        ` · ${fmtDur(
                          (new Date(e.fin).getTime() - new Date(e.inicio).getTime()) /
                            1000
                        )}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => setEditando(e)}
                      title="Corregir inicio/fin"
                      className="opacity-0 group-hover:opacity-100 text-faint hover:text-brand transition"
                    >
                      ✎
                    </button>
                    <button
                      onClick={async () => {
                        if (!window.confirm('¿Eliminar esta sesión?')) return
                        await api.deleteTimeEntry(e.id)
                        cargar()
                      }}
                      className="opacity-0 group-hover:opacity-100 text-faint hover:text-[color:var(--c-danger)] transition"
                    >
                      ✕
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {editando && (
        <EditorSesion
          entry={editando}
          onCerrar={() => setEditando(null)}
          onGuardado={() => {
            setEditando(null)
            cargar()
          }}
        />
      )}
    </div>
  )
}

function EditorSesion({
  entry,
  onCerrar,
  onGuardado,
}: {
  entry: TimeEntry
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [inicio, setInicio] = useState(aLocalInput(entry.inicio))
  const [fin, setFin] = useState(entry.fin ? aLocalInput(entry.fin) : '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const guardar = async () => {
    setError('')
    setBusy(true)
    try {
      await api.updateTimeEntry(entry.id, {
        inicio: aISO(inicio),
        ...(fin ? { fin: aISO(fin) } : {}),
      })
      onGuardado()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo guardar')
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4"
      onClick={onCerrar}
    >
      <div
        className="card w-full max-w-sm p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-serif text-xl">Corregir sesión</h3>
        <p className="text-sm text-muted truncate">
          {entry.tarea}
          {entry.proyecto && ` · ${entry.proyecto}`}
        </p>
        <label className="text-xs text-muted flex flex-col gap-1">
          Inicio
          <input
            type="datetime-local"
            value={inicio}
            onChange={(e) => setInicio(e.target.value)}
            className="input"
          />
        </label>
        <label className="text-xs text-muted flex flex-col gap-1">
          Fin {entry.fin === null && '(vacío = sigue corriendo)'}
          <input
            type="datetime-local"
            value={fin}
            onChange={(e) => setFin(e.target.value)}
            className="input"
          />
        </label>
        {error && <p className="text-[color:var(--c-danger)] text-sm">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onCerrar} className="btn-ghost btn">
            Cancelar
          </button>
          <button onClick={guardar} disabled={busy} className="btn">
            {busy ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}
