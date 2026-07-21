import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { aISOColombia, api, ApiError, type Reminder } from '../api'

function efectivo(r: Reminder): string {
  return r.pospuesto_para ?? r.disparar_en
}

// Colapsa la escalera de avisos: por cada origen (responsabilidad, tarea…) deja
// solo el más reciente/urgente. Los manuales (sin origen) quedan tal cual.
function colapsarPorOrigen(reminders: Reminder[]): Reminder[] {
  const porOrigen = new Map<string, Reminder>()
  for (const r of reminders) {
    const key = r.origen_id ? `${r.origen_tipo}:${r.origen_id}` : `manual:${r.id}`
    const prev = porOrigen.get(key)
    if (!prev || new Date(efectivo(r)) > new Date(efectivo(prev))) {
      porOrigen.set(key, r)
    }
  }
  return [...porOrigen.values()].sort(
    (a, b) => new Date(efectivo(a)).getTime() - new Date(efectivo(b)).getTime()
  )
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
  const [recurrencia, setRecurrencia] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)

  // Por defecto: solo los que ya llegaron (evita mostrar la escalera de avisos
  // futuros). Con "Ver resueltos": el histórico resuelto.
  const cargar = () =>
    (verResueltos ? api.listReminders(true) : api.listDueReminders())
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
      await api.createReminder(texto.trim(), aISOColombia(cuando), recurrencia || null)
      setTexto('')
      setCuando('')
      setRecurrencia('')
      cargar()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al crear')
    }
  }

  const ahora = Date.now()

  // Vista por defecto: escalera colapsada a un aviso por origen. Con "Ver
  // resueltos" mostramos el histórico completo, sin colapsar.
  const visibles = useMemo(
    () => (verResueltos ? reminders : colapsarPorOrigen(reminders)),
    [reminders, verResueltos]
  )

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-2xl">Recordatorios</h2>
        <label className="text-sm text-muted flex items-center gap-2">
          <input
            type="checkbox"
            checked={verResueltos}
            onChange={(e) => setVerResueltos(e.target.checked)}
            className="accent-[color:var(--c-teal)]"
          />
          Ver resueltos
        </label>
      </div>

      <form onSubmit={crear} className="flex flex-wrap gap-2">
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="¿Qué te recuerdo?"
          className="input flex-1 min-w-52"
        />
        <input
          value={cuando}
          onChange={(e) => setCuando(e.target.value)}
          type="datetime-local"
          min="2000-01-01T00:00"
          max="9999-12-31T23:59"
          className="input w-auto"
        />
        <select
          value={recurrencia}
          onChange={(e) => setRecurrencia(e.target.value)}
          className="input w-auto"
          title="Repetir: al resolverlo, vuelve el siguiente periodo"
        >
          <option value="">No se repite</option>
          <option value="diaria">Diario</option>
          <option value="semanal">Semanal</option>
          <option value="mensual">Mensual</option>
          <option value="trimestral">Trimestral</option>
          <option value="anual">Anual</option>
        </select>
        <button className="btn">Crear</button>
      </form>
      {error && <p className="text-[color:var(--c-danger)] text-sm">{error}</p>}

      {cargando ? (
        <p className="text-faint">Cargando…</p>
      ) : visibles.length === 0 ? (
        <p className="text-faint">Sin recordatorios.</p>
      ) : (
        <ul className="space-y-2">
          {visibles.map((r) => {
            const venc = new Date(efectivo(r)).getTime() <= ahora && !r.resuelto
            return (
              <li
                key={r.id}
                className="group card px-4 py-3 flex items-start justify-between gap-3"
              >
                <div>
                  <p className={r.resuelto ? 'line-through text-faint' : ''}>
                    {r.texto}
                    {r.recurrencia && (
                      <span className="badge ml-2 text-xs">🔁 {r.recurrencia}</span>
                    )}
                  </p>
                  <p className="text-xs mt-1">
                    <span className={venc ? 'text-[color:var(--c-danger)]' : 'text-faint'}>
                      {venc ? '⏰ vencido · ' : ''}
                      {new Date(efectivo(r)).toLocaleString('es-CO')}
                    </span>
                    {r.veces_avisado > 0 && (
                      <span className="text-faint ml-2">
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
                      className="btn-ghost btn text-sm py-1"
                    >
                      Posponer
                    </button>
                    <button
                      onClick={async () => {
                        await api.resolveReminder(r.id)
                        cargar()
                      }}
                      className="btn text-sm py-1"
                      style={{ background: 'var(--c-green)', color: '#fff' }}
                    >
                      Resolver
                    </button>
                    <button
                      onClick={async () => {
                        if (!window.confirm('¿Eliminar este recordatorio?')) return
                        await api.deleteReminder(r.id)
                        cargar()
                      }}
                      className="opacity-0 group-hover:opacity-100 text-faint hover:text-[color:var(--c-danger)] transition"
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
