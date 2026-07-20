import { useEffect, useState, type FormEvent } from 'react'
import {
  api,
  ApiError,
  fmtMoney,
  type Account,
  type Category,
  type Responsibility,
} from '../api'

const RECURRENCIAS = ['diaria', 'semanal', 'mensual', 'trimestral', 'anual']

export default function Responsabilidades() {
  const [items, setItems] = useState<Responsibility[]>([])
  const [cuentas, setCuentas] = useState<Account[]>([])
  const [categorias, setCategorias] = useState<Category[]>([])
  const [nombre, setNombre] = useState('')
  const [recurrencia, setRecurrencia] = useState('mensual')
  const [venc, setVenc] = useState('')
  const [monto, setMonto] = useState('')
  const [cuentaId, setCuentaId] = useState('')
  const [categoriaId, setCategoriaId] = useState('')
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [cargando, setCargando] = useState(true)

  const cargar = () =>
    api.listResponsibilities().then(setItems).finally(() => setCargando(false))

  useEffect(() => {
    cargar()
    api.listAccounts().then(setCuentas)
    api.listCategories().then(setCategorias)
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
        monto ? Number(monto) : null,
        cuentaId || null,
        categoriaId || null
      )
      setNombre('')
      setVenc('')
      setMonto('')
      setCuentaId('')
      setCategoriaId('')
      cargar()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al crear')
    }
  }

  const registrarPago = async (r: Responsibility) => {
    setError('')
    setAviso('')
    try {
      const res = await api.payResponsibility(r.id)
      if (res.gasto_creado) {
        setAviso(
          `Pago registrado: $${fmtMoney(res.monto ?? 0)} desde ${res.cuenta}. ` +
            `Próximo vencimiento actualizado.`
        )
      } else {
        setAviso(`«${r.nombre}» marcada como pagada. Próximo vencimiento actualizado.`)
      }
      cargar()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al registrar el pago')
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <h2 className="font-serif text-2xl">Responsabilidades</h2>
      <p className="text-sm text-muted">
        Compromisos que se repiten (arriendo, administración, renovaciones). Si les
        pones cuenta y monto, al registrar el pago se crea el gasto en finanzas.
      </p>

      <form onSubmit={crear} className="flex flex-wrap gap-2">
        <input
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Compromiso (arriendo, administración…)"
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
          title="Próximo vencimiento"
        />
        <input
          value={monto}
          onChange={(e) => setMonto(e.target.value)}
          type="number"
          placeholder="monto (opcional)"
          className="input w-40"
        />
        <select
          value={cuentaId}
          onChange={(e) => setCuentaId(e.target.value)}
          className="input w-auto"
          title="Cuenta de donde sale el dinero (opcional)"
        >
          <option value="">— cuenta —</option>
          {cuentas.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre}
            </option>
          ))}
        </select>
        <select
          value={categoriaId}
          onChange={(e) => setCategoriaId(e.target.value)}
          className="input w-auto"
          title="Categoría del gasto (opcional)"
        >
          <option value="">— categoría —</option>
          {categorias.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre}
            </option>
          ))}
        </select>
        <button className="btn">Crear</button>
      </form>
      {error && <p className="text-[color:var(--c-danger)] text-sm">{error}</p>}
      {aviso && <p className="text-[color:var(--c-green)] text-sm">{aviso}</p>}

      {cargando ? (
        <p className="text-faint">Cargando…</p>
      ) : items.length === 0 ? (
        <p className="text-faint">Sin responsabilidades.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((r) => {
            const puedePagar = !!r.account_id && !!r.monto
            return (
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
                    {r.cuenta && ` · ${r.cuenta}`}
                    {r.categoria && ` · ${r.categoria}`}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0 text-sm">
                  <button
                    onClick={() => registrarPago(r)}
                    className="btn text-sm py-1"
                    style={{ background: 'var(--c-green)', color: '#fff' }}
                    title={
                      puedePagar
                        ? 'Registrar el pago (crea el gasto en finanzas y avanza la fecha)'
                        : 'Marcar como pagada (avanza la fecha; sin gasto por no tener cuenta y monto)'
                    }
                  >
                    {puedePagar ? 'Registrar pago' : 'Pagada'}
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
            )
          })}
        </ul>
      )}
    </div>
  )
}
