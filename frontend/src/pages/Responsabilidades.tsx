import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, fmtMoney, type Responsibility } from '../api'

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
      <h2 className="font-serif text-2xl">Responsabilidades</h2>

      <form onSubmit={crear} className="flex flex-wrap gap-2">
        <input
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Compromiso (arriendo, renovación…)"
          className="input flex-1 min-w-48"
        />
        <select
          value={recurrencia}
          onChange={(e) => setRecurrencia(e.target.value)}
          className="input w-auto"
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
          className="input w-auto"
        />
        <input
          value={monto}
          onChange={(e) => setMonto(e.target.value)}
          type="number"
          placeholder="monto (opcional)"
          className="input w-40"
        />
        <button className="btn">Crear</button>
      </form>
      {error && <p className="text-[color:var(--c-danger)] text-sm">{error}</p>}

      {cargando ? (
        <p className="text-faint">Cargando…</p>
      ) : items.length === 0 ? (
        <p className="text-faint">Sin responsabilidades.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((r) => (
            <li
              key={r.id}
              className="group card px-4 py-3 flex items-center justify-between gap-3"
            >
              <div>
                <p className="font-medium">{r.nombre}</p>
                <p className="text-xs text-muted mt-1">
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
                  className="btn text-sm py-1"
                  style={{ background: 'var(--c-green)', color: '#fff' }}
                  title="Marcar cumplida (recalcula el próximo vencimiento)"
                >
                  Cumplida
                </button>
                <button
                  onClick={async () => {
                    if (!window.confirm('¿Eliminar esta responsabilidad?')) return
                    await api.deleteResponsibility(r.id)
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
      )}
    </div>
  )
}
