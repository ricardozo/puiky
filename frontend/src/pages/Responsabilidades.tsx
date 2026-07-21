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
  const [editando, setEditando] = useState<Responsibility | null>(null)
  const [pagando, setPagando] = useState<Responsibility | null>(null)

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

  const eliminar = async (r: Responsibility) => {
    if (!window.confirm(`¿Eliminar la responsabilidad «${r.nombre}»?`)) return
    await api.deleteResponsibility(r.id)
    cargar()
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {editando && (
        <EditorResponsabilidad
          resp={editando}
          cuentas={cuentas}
          categorias={categorias}
          onCerrar={() => setEditando(null)}
          onGuardado={() => {
            setEditando(null)
            cargar()
          }}
        />
      )}
      {pagando && (
        <PagoModal
          resp={pagando}
          cuentas={cuentas}
          onCerrar={() => setPagando(null)}
          onPagado={(msg) => {
            setPagando(null)
            setAviso(msg)
            cargar()
          }}
        />
      )}

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
          {items.map((r) => (
            <li
              key={r.id}
              className="card px-4 py-3 flex flex-wrap items-center justify-between gap-3"
            >
              <div className="min-w-0">
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
                  onClick={() => setPagando(r)}
                  className="btn text-sm py-1"
                  style={{ background: 'var(--c-green)', color: '#fff' }}
                  title="Registrar el pago (puedes ajustar el monto de este mes)"
                >
                  Registrar pago
                </button>
                <button
                  onClick={() => setEditando(r)}
                  className="btn-ghost btn text-sm py-1"
                  title="Editar"
                >
                  Editar
                </button>
                <button
                  onClick={() => eliminar(r)}
                  className="text-faint hover:text-[color:var(--c-danger)] transition px-1"
                  title="Eliminar"
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

// --- Modal: registrar pago (monto ajustable para pagos que varían, p. ej. USD) ---

function PagoModal({
  resp,
  cuentas,
  onCerrar,
  onPagado,
}: {
  resp: Responsibility
  cuentas: Account[]
  onCerrar: () => void
  onPagado: (mensaje: string) => void
}) {
  const [monto, setMonto] = useState(resp.monto ?? '')
  const [cuentaId, setCuentaId] = useState(resp.account_id ?? '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const confirmar = async () => {
    setBusy(true)
    setError('')
    try {
      const res = await api.payResponsibility(resp.id, {
        monto: monto ? Number(monto) : null,
        account_id: cuentaId || null,
      })
      const msg = res.gasto_creado
        ? `Pago registrado: $${fmtMoney(res.monto ?? 0)} desde ${res.cuenta}. Próximo vencimiento actualizado.`
        : `«${resp.nombre}» marcada como pagada. Próximo vencimiento actualizado.`
      onPagado(msg)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo registrar el pago')
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4"
      onClick={onCerrar}
    >
      <div className="card w-full max-w-md p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-serif text-xl">Registrar pago · {resp.nombre}</h3>
        <p className="text-xs text-muted">
          Ajusta el monto si este mes cambió (p. ej. pagos en dólares). Déjalo vacío
          para solo marcar como cumplida sin registrar gasto.
        </p>

        <label className="text-xs text-muted flex flex-col gap-1">
          Monto de este pago
          <input
            type="number"
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            placeholder="monto"
            className="input"
            autoFocus
          />
        </label>

        <label className="text-xs text-muted flex flex-col gap-1">
          Cuenta de donde sale
          <select
            value={cuentaId}
            onChange={(e) => setCuentaId(e.target.value)}
            className="input"
          >
            <option value="">— sin cuenta (no crea gasto) —</option>
            {cuentas.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>

        {error && <p className="text-[color:var(--c-danger)] text-sm">{error}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onCerrar} className="btn-ghost btn">
            Cancelar
          </button>
          <button
            onClick={confirmar}
            disabled={busy}
            className="btn"
            style={{ background: 'var(--c-green)', color: '#fff' }}
          >
            {busy ? 'Registrando…' : 'Confirmar pago'}
          </button>
        </div>
      </div>
    </div>
  )
}

// --- Modal: editar responsabilidad ---

function EditorResponsabilidad({
  resp,
  cuentas,
  categorias,
  onCerrar,
  onGuardado,
}: {
  resp: Responsibility
  cuentas: Account[]
  categorias: Category[]
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [nombre, setNombre] = useState(resp.nombre)
  const [recurrencia, setRecurrencia] = useState(resp.recurrencia)
  const [venc, setVenc] = useState(resp.proximo_venc)
  const [monto, setMonto] = useState(resp.monto ?? '')
  const [cuentaId, setCuentaId] = useState(resp.account_id ?? '')
  const [categoriaId, setCategoriaId] = useState(resp.category_id ?? '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // Si la recurrencia guardada no está en la lista (p. ej. cada_N_dias), la añadimos.
  const opciones = RECURRENCIAS.includes(recurrencia)
    ? RECURRENCIAS
    : [recurrencia, ...RECURRENCIAS]

  const guardar = async () => {
    setBusy(true)
    setError('')
    try {
      await api.updateResponsibility(resp.id, {
        nombre: nombre.trim(),
        recurrencia,
        proximo_venc: venc,
        monto: monto ? Number(monto) : null,
        account_id: cuentaId || null,
        category_id: categoriaId || null,
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
      <div className="card w-full max-w-md p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-serif text-xl">Editar responsabilidad</h3>

        <label className="text-xs text-muted flex flex-col gap-1">
          Nombre
          <input value={nombre} onChange={(e) => setNombre(e.target.value)} className="input" />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs text-muted flex flex-col gap-1">
            Recurrencia
            <select
              value={recurrencia}
              onChange={(e) => setRecurrencia(e.target.value)}
              className="input"
            >
              {opciones.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-muted flex flex-col gap-1">
            Próximo vencimiento
            <input
              type="date"
              value={venc}
              min="2000-01-01"
              max="9999-12-31"
              onChange={(e) => setVenc(e.target.value)}
              className="input"
            />
          </label>
        </div>

        <label className="text-xs text-muted flex flex-col gap-1">
          Monto (opcional)
          <input
            type="number"
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            placeholder="monto"
            className="input"
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs text-muted flex flex-col gap-1">
            Cuenta
            <select
              value={cuentaId}
              onChange={(e) => setCuentaId(e.target.value)}
              className="input"
            >
              <option value="">— cuenta —</option>
              {cuentas.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-muted flex flex-col gap-1">
            Categoría
            <select
              value={categoriaId}
              onChange={(e) => setCategoriaId(e.target.value)}
              className="input"
            >
              <option value="">— categoría —</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
        </div>

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
