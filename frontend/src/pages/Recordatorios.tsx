import { useEffect, useState, type FormEvent } from 'react'
import { aISOColombia, api, ApiError, type Reminder } from '../api'

const inputCls =
  'rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 outline-none focus:border-indigo-500'

function efectivo(r: Reminder): string {
  return r.pospuesto_para ?? r.disparar_en
}

function mananaNueve(): string {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return aISOColombia(`${yyyy}-${mm}-${dd}T09:00`)
}

export default function Recordatorios() {
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [verResueltos, setVerResueltos] = useState(false)
  const [texto, setTexto] = useState('')
  const [cuando, setCuando] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)

  const cargar = () =>
    api
      .listReminders(verResueltos ? undefined : false)
      .then(setReminders)
      .finally(() => setCargando(false))

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [verResueltos])

  const crear = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (!texto.trim() || !cuando) return
    const anio = Number(cuando.slice(0, 4))
    if (anio < 2000 || anio > 9999) {
      setError('La fecha no es válida.')
      return
    }
    try {
      await api.createReminder(texto.trim(), aISOColombia(cuando))
      setTexto('')
      setCuando('')
      cargar()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al crear')
    }
  }

  const ahora = Date.now()

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Recordatorios</h2>
        <label className="text-sm text-slate-400 flex items-center gap-2">
          <input
            type="checkbox"
            checked={verResueltos}
            onChange={(e) => setVerResueltos(e.target.checked)}
          />
          Ver resueltos
        </label>
      </div>

      <form onSubmit={crear} className="flex flex-wrap gap-2">
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="¿Qué te recuerdo?"
          className={`${inputCls} flex-1 min-w-52`}
        />
        <input
          value={cuando}
          onChange={(e) => setCuando(e.target.value)}
          type="datetime-local"
          min="2000-01-01T00:00"
          max="9999-12-31T23:59"
          className={inputCls}
        />
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Crear
        </button>
      </form>
      {error && <p className="text-red-400 text-sm">{error}</p>}

      {cargando ? (
        <p className="text-slate-500">Cargando…</p>
      ) : reminders.length === 0 ? (
        <p className="text-slate-500">Sin recordatorios.</p>
      ) : (
        <ul className="space-y-2">
          {reminders.map((r) => {
            const venc = new Date(efectivo(r)).getTime() <= ahora && !r.resuelto
            return (
              <li
                key={r.id}
                className="group rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-3 flex items-start justify-between gap-3"
              >
                <div>
                  <p className={r.resuelto ? 'line-through text-slate-500' : ''}>
                    {r.texto}
                  </p>
                  <p className="text-xs mt-1">
                    <span className={venc ? 'text-red-400' : 'text-slate-500'}>
                      {venc ? '⏰ vencido · ' : ''}
                      {new Date(efectivo(r)).toLocaleString('es-CO')}
                    </span>
                    {r.veces_avisado > 0 && (
                      <span className="text-slate-500 ml-2">
                        · avisado {r.veces_avisado}×
                      </span>
                    )}
                  </p>
                </div>
                {!r.resuelto && (
                  <div className="flex items-center gap-2 shrink-0 text-sm">
                    <button
                      onClick={async () => {
                        await api.snoozeReminder(r.id, mananaNueve())
                        cargar()
                      }}
                      className="rounded border border-slate-700 px-2 py-1 text-slate-300 hover:bg-slate-800"
                    >
                      Posponer
                    </button>
                    <button
                      onClick={async () => {
                        await api.resolveReminder(r.id)
                        cargar()
                      }}
                      className="rounded bg-emerald-600/80 hover:bg-emerald-600 px-2 py-1"
                    >
                      Resolver
                    </button>
                    <button
                      onClick={async () => {
                        await api.deleteReminder(r.id)
                        cargar()
                      }}
                      className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition"
                    >
                      ✕
                    </button>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
