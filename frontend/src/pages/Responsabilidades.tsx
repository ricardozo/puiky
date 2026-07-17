import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, fmtMoney, type Responsibility } from '../api'

const inputCls =
  'rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 outline-none focus:border-indigo-500'

const RECURRENCIAS = ['diaria', 'semanal', 'mensual', 'trimestral', 'anual']

export default function Responsabilidades() {
  const [items, setItems] = useState<Responsibility[]>([])
  const [nombre, setNombre] = useState('')
  const [recurrencia, setRecurrencia] = useState('mensual')
  const [venc, setVenc] = useState('')
  const [monto, setMonto] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)

  const cargar = () =>
    api.listResponsibilities().then(setItems).finally(() => setCargando(false))

  useEffect(() => {
    cargar()
  }, [])

  const crear = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (!nombre.trim() || !venc) return
    const anio = Number(venc.slice(0, 4))
    if (anio < 2000 || anio > 9999) {
      setError('La fecha de vencimiento no es válida.')
      return
    }
    try {
      await api.createResponsibility(
        nombre.trim(),
        recurrencia,
        venc,
        monto ? Number(monto) : null
      )
      setNombre('')
      setVenc('')
      setMonto('')
      cargar()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al crear')
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <h2 className="text-xl font-semibold">Responsabilidades</h2>

      <form onSubmit={crear} className="flex flex-wrap gap-2">
        <input
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Compromiso (arriendo, renovación…)"
          className={`${inputCls} flex-1 min-w-48`}
        />
        <select
          value={recurrencia}
          onChange={(e) => setRecurrencia(e.target.value)}
          className={inputCls}
        >
          {RECURRENCIAS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <input
          value={venc}
          onChange={(e) => setVenc(e.target.value)}
          type="date"
          min="2000-01-01"
          max="9999-12-31"
          className={inputCls}
        />
        <input
          value={monto}
          onChange={(e) => setMonto(e.target.value)}
          type="number"
          placeholder="monto (opcional)"
          className={`${inputCls} w-40`}
        />
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Crear
        </button>
      </form>
      {error && <p className="text-red-400 text-sm">{error}</p>}

      {cargando ? (
        <p className="text-slate-500">Cargando…</p>
      ) : items.length === 0 ? (
        <p className="text-slate-500">Sin responsabilidades.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((r) => (
            <li
              key={r.id}
              className="group rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-3 flex items-center justify-between gap-3"
            >
              <div>
                <p className="font-medium">{r.nombre}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {r.recurrencia} · próximo:{' '}
                  {new Date(r.proximo_venc + 'T00:00').toLocaleDateString('es-CO')}
                  {r.monto && ` · $${fmtMoney(r.monto)}`}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0 text-sm">
                <button
                  onClick={async () => {
                    await api.fulfillResponsibility(r.id)
                    cargar()
                  }}
                  className="rounded bg-emerald-600/80 hover:bg-emerald-600 px-2 py-1"
                  title="Marcar cumplida (recalcula el próximo vencimiento)"
                >
                  Cumplida
                </button>
                <button
                  onClick={async () => {
                    await api.deleteResponsibility(r.id)
                    cargar()
                  }}
                  className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition"
                >
                  ✕
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
