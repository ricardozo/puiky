import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  api,
  ApiError,
  exportFinanzasExcel,
  fmtMoney,
  type Account,
  type BudgetProgress,
  type Category,
  type Transaction,
} from '../api'

type ExportFiltro = {
  accountId?: string
  categoryId?: string
  desde?: string
  hasta?: string
}

function BotonExcel({ filtro, label = 'Exportar a Excel' }: { filtro?: ExportFiltro; label?: string }) {
  const [busy, setBusy] = useState(false)
  const bajar = async () => {
    setBusy(true)
    try {
      await exportFinanzasExcel(filtro)
    } catch {
      alert('No se pudo exportar el Excel.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <button onClick={bajar} disabled={busy} className="btn-gold btn text-sm py-1.5">
      {busy ? 'Generando…' : `⬇ ${label}`}
    </button>
  )
}

// Modal para editar un movimiento (no cambia el tipo). Los saldos se ajustan
// solos en el backend (revierte el efecto viejo, aplica el nuevo).
function EditorMovimiento({
  tx,
  accounts,
  categories,
  onCerrar,
  onGuardado,
}: {
  tx: Transaction
  accounts: Account[]
  categories: Category[]
  onCerrar: () => void
  onGuardado: () => void
}) {
  const esTransfer = tx.tipo === 'transferencia'
  const [monto, setMonto] = useState(String(tx.monto))
  const [cuenta, setCuenta] = useState(tx.account_id)
  const [destino, setDestino] = useState(tx.cuenta_destino_id ?? '')
  const [categoria, setCategoria] = useState(tx.category_id ?? '')
  const [fecha, setFecha] = useState(tx.fecha)
  const [nota, setNota] = useState(tx.nota ?? '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const guardar = async () => {
    setBusy(true)
    setError('')
    try {
      await api.updateTransaction(tx.id, {
        monto: Number(monto),
        account_id: cuenta,
        cuenta_destino_id: esTransfer ? destino : null,
        category_id: esTransfer ? null : categoria || null,
        fecha,
        nota: nota.trim() || null,
      })
      onGuardado()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo guardar')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4"
      onClick={onCerrar}
    >
      <div
        className="card w-full max-w-md p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h3 className="font-serif text-xl">Editar movimiento</h3>
          <span className="badge">{tx.tipo}</span>
        </div>

        <label className="text-xs text-muted flex flex-col gap-1">
          Monto
          <input
            type="number"
            value={monto}
            onChange={(e) => setMonto(e.target.value)}
            className="input"
          />
        </label>

        <label className="text-xs text-muted flex flex-col gap-1">
          {esTransfer ? 'Cuenta origen' : 'Cuenta'}
          <select value={cuenta} onChange={(e) => setCuenta(e.target.value)} className="input">
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.nombre}
              </option>
            ))}
          </select>
        </label>

        {esTransfer ? (
          <label className="text-xs text-muted flex flex-col gap-1">
            Cuenta destino
            <select
              value={destino}
              onChange={(e) => setDestino(e.target.value)}
              className="input"
            >
              <option value="">—</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nombre}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label className="text-xs text-muted flex flex-col gap-1">
            Categoría
            <select
              value={categoria}
              onChange={(e) => setCategoria(e.target.value)}
              className="input"
            >
              <option value="">—</option>
              {categories
                .filter((c) => c.activa || c.id === tx.category_id)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
            </select>
          </label>
        )}

        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs text-muted flex flex-col gap-1">
            Fecha
            <input
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              className="input"
            />
          </label>
          <label className="text-xs text-muted flex flex-col gap-1">
            Nota
            <input
              value={nota}
              onChange={(e) => setNota(e.target.value)}
              placeholder="opcional"
              className="input"
            />
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

type Vista =
  | { tipo: 'panel' }
  | { tipo: 'cuenta'; account: Account }
  | { tipo: 'categoria'; category: Category }

// --- utilidades de fecha (local, sin corrimiento UTC) ---
function ymd(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}
const inicioMes = () => {
  const d = new Date()
  return ymd(new Date(d.getFullYear(), d.getMonth(), 1))
}
const hoyStr = () => ymd(new Date())

const verde = 'text-[color:var(--c-green)]'
const rojo = 'text-[color:var(--c-danger)]'

export default function Finanzas() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [budgets, setBudgets] = useState<BudgetProgress[]>([])
  const [cargando, setCargando] = useState(true)
  const [vista, setVista] = useState<Vista>({ tipo: 'panel' })

  const cargar = useCallback(async () => {
    const [acc, cats, txs, buds] = await Promise.all([
      api.listAccounts(),
      api.listCategories(false),
      api.listTransactions(),
      api.listBudgets(),
    ])
    const prog = await Promise.all(buds.map((b) => api.budgetProgress(b.id)))
    setAccounts(acc)
    setCategories(cats)
    setTransactions(txs)
    setBudgets(prog)
    setCargando(false)
  }, [])

  useEffect(() => {
    cargar()
  }, [cargar])

  const nombreCuenta = useCallback(
    (id: string | null) => accounts.find((a) => a.id === id)?.nombre ?? '—',
    [accounts]
  )
  const nombreCategoria = useCallback(
    (id: string | null) =>
      id ? categories.find((c) => c.id === id)?.nombre ?? '—' : '(sin categoría)',
    [categories]
  )

  const volver = () => {
    cargar()
    setVista({ tipo: 'panel' })
  }

  if (cargando) return <p className="text-faint">Cargando…</p>

  if (vista.tipo === 'cuenta') {
    const acc = vista.account
    return (
      <DetalleLibro
        titulo={acc.nombre}
        subtitulo={acc.tipo}
        saldoActual={acc.saldo}
        exportBase={{ accountId: acc.id }}
        accounts={accounts}
        categories={categories}
        onVolver={volver}
        fetchTxs={(desde, hasta) => api.listTransactions({ desde, hasta })}
        clasificar={(tx) => {
          if (tx.account_id === acc.id && tx.tipo === 'gasto')
            return { lado: 'salida', etiqueta: nombreCategoria(tx.category_id) }
          if (tx.account_id === acc.id && tx.tipo === 'ingreso')
            return { lado: 'entrada', etiqueta: nombreCategoria(tx.category_id) }
          if (tx.tipo === 'transferencia' && tx.cuenta_destino_id === acc.id)
            return { lado: 'entrada', etiqueta: `desde ${nombreCuenta(tx.account_id)}` }
          if (tx.tipo === 'transferencia' && tx.account_id === acc.id)
            return {
              lado: 'salida',
              etiqueta: `hacia ${nombreCuenta(tx.cuenta_destino_id)}`,
            }
          return null
        }}
      />
    )
  }

  if (vista.tipo === 'categoria') {
    const cat = vista.category
    return (
      <DetalleLibro
        titulo={cat.nombre}
        subtitulo="categoría"
        exportBase={{ categoryId: cat.id }}
        accounts={accounts}
        categories={categories}
        onVolver={volver}
        fetchTxs={(desde, hasta) =>
          api.listTransactions({ categoryId: cat.id, desde, hasta })
        }
        clasificar={(tx) => {
          if (tx.tipo === 'gasto')
            return { lado: 'salida', etiqueta: nombreCuenta(tx.account_id) }
          if (tx.tipo === 'ingreso')
            return { lado: 'entrada', etiqueta: nombreCuenta(tx.account_id) }
          return null
        }}
      />
    )
  }

  const total = accounts.reduce((s, a) => s + Number(a.saldo), 0)

  return (
    <div className="space-y-9 max-w-4xl">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-serif text-2xl">Finanzas</h2>
        <BotonExcel />
      </div>

      <Cuentas
        accounts={accounts}
        total={total}
        onCambio={cargar}
        onAbrir={(account) => setVista({ tipo: 'cuenta', account })}
      />
      <PorCategoria
        categories={categories}
        transactions={transactions}
        onAbrir={(category) => setVista({ tipo: 'categoria', category })}
      />
      <Movimiento accounts={accounts} categories={categories} onCambio={cargar} />
      <Movimientos
        transactions={transactions}
        accounts={accounts}
        categories={categories}
        nombreCuenta={nombreCuenta}
        nombreCategoria={nombreCategoria}
        onCambio={cargar}
      />
      <Presupuestos
        budgets={budgets}
        categories={categories}
        nombreCategoria={nombreCategoria}
        onCambio={cargar}
      />
    </div>
  )
}

// --- Cuentas ---

function Cuentas({
  accounts,
  total,
  onCambio,
  onAbrir,
}: {
  accounts: Account[]
  total: number
  onCambio: () => void
  onAbrir: (a: Account) => void
}) {
  const [nombre, setNombre] = useState('')
  const [tipo, setTipo] = useState('efectivo')
  const [saldo, setSaldo] = useState('')

  const crear = async (e: FormEvent) => {
    e.preventDefault()
    if (!nombre.trim()) return
    await api.createAccount(nombre.trim(), tipo, Number(saldo) || 0)
    setNombre('')
    setSaldo('')
    onCambio()
  }

  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h3 className="eyebrow">Cuentas</h3>
        <span className="text-sm text-muted">
          Total: <span className="text-ink font-medium">${fmtMoney(total)}</span>
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {accounts.map((a) => (
          <button
            key={a.id}
            onClick={() => onAbrir(a)}
            className="card text-left p-4 hover:border-teal transition"
          >
            <div className="text-sm text-muted">{a.nombre}</div>
            <div className="text-lg font-semibold">${fmtMoney(a.saldo)}</div>
            <div className="text-xs text-faint mt-1">{a.tipo} · ver movimientos →</div>
          </button>
        ))}
      </div>
      <form onSubmit={crear} className="flex flex-wrap gap-2">
        <input
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Nueva cuenta"
          className="input w-auto"
        />
        <input
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          placeholder="tipo (efectivo/banco/…)"
          className="input w-auto"
        />
        <input
          value={saldo}
          onChange={(e) => setSaldo(e.target.value)}
          type="number"
          placeholder="saldo inicial"
          className="input w-36"
        />
        <button className="btn">Añadir</button>
      </form>
    </section>
  )
}

// --- Panel: resultado por categoría (mes actual) ---

function PorCategoria({
  categories,
  transactions,
  onAbrir,
}: {
  categories: Category[]
  transactions: Transaction[]
  onAbrir: (c: Category) => void
}) {
  const desde = inicioMes()
  const filas = useMemo(() => {
    const acumulado = new Map<string, number>()
    for (const t of transactions) {
      if (!t.category_id || t.fecha < desde) continue
      if (t.tipo !== 'gasto' && t.tipo !== 'ingreso') continue
      const signo = t.tipo === 'ingreso' ? 1 : -1
      acumulado.set(
        t.category_id,
        (acumulado.get(t.category_id) ?? 0) + signo * Number(t.monto)
      )
    }
    return categories
      .filter((c) => acumulado.has(c.id))
      .map((c) => ({ cat: c, neto: acumulado.get(c.id) as number }))
      .sort((a, b) => Math.abs(b.neto) - Math.abs(a.neto))
  }, [categories, transactions, desde])

  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h3 className="eyebrow">Por categoría · este mes</h3>
        <span className="text-xs text-faint">clic para ver el detalle</span>
      </div>
      {filas.length === 0 ? (
        <p className="text-faint text-sm">Sin movimientos con categoría este mes.</p>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2">
          {filas.map(({ cat, neto }) => (
            <button
              key={cat.id}
              onClick={() => onAbrir(cat)}
              className="card flex items-center justify-between px-4 py-3 text-sm hover:border-teal transition"
            >
              <span className="font-medium">{cat.nombre}</span>
              <span className={neto >= 0 ? verde : rojo}>
                {neto >= 0 ? '+' : '−'}${fmtMoney(Math.abs(neto))}
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  )
}

// --- Registrar movimiento ---

function Movimiento({
  accounts,
  categories,
  onCambio,
}: {
  accounts: Account[]
  categories: Category[]
  onCambio: () => void
}) {
  const [tipo, setTipo] = useState('gasto')
  const [monto, setMonto] = useState('')
  const [cuenta, setCuenta] = useState('')
  const [destino, setDestino] = useState('')
  const [categoria, setCategoria] = useState('')
  const [nota, setNota] = useState('')
  const [error, setError] = useState('')

  const esTransfer = tipo === 'transferencia'

  const registrar = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await api.createTransaction({
        tipo,
        monto: Number(monto),
        account_id: cuenta,
        cuenta_destino_id: esTransfer ? destino : null,
        category_id: esTransfer ? null : categoria || null,
        nota: nota || null,
      })
      setMonto('')
      setNota('')
      onCambio()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error registrando')
    }
  }

  return (
    <section className="space-y-3">
      <h3 className="eyebrow">Registrar movimiento</h3>
      <form onSubmit={registrar} className="flex flex-wrap items-center gap-2">
        <select
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          className="input w-auto"
        >
          <option value="gasto">Gasto</option>
          <option value="ingreso">Ingreso</option>
          <option value="transferencia">Transferencia</option>
        </select>
        <input
          value={monto}
          onChange={(e) => setMonto(e.target.value)}
          type="number"
          placeholder="monto"
          className="input w-32"
        />
        <select
          value={cuenta}
          onChange={(e) => setCuenta(e.target.value)}
          className="input w-auto"
        >
          <option value="">{esTransfer ? 'Desde…' : 'Cuenta…'}</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.nombre}
            </option>
          ))}
        </select>
        {esTransfer ? (
          <select
            value={destino}
            onChange={(e) => setDestino(e.target.value)}
            className="input w-auto"
          >
            <option value="">Hacia…</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.nombre}
              </option>
            ))}
          </select>
        ) : (
          <select
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
            className="input w-auto"
          >
            <option value="">Categoría…</option>
            {categories
              .filter((c) => c.activa)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
          </select>
        )}
        <input
          value={nota}
          onChange={(e) => setNota(e.target.value)}
          placeholder="nota (opcional)"
          className="input flex-1 min-w-40"
        />
        <button className="btn">Registrar</button>
      </form>
      {error && <p className={`${rojo} text-sm`}>{error}</p>}
    </section>
  )
}

// --- Movimientos recientes ---

const signoTipo: Record<string, { s: string; cls: string }> = {
  gasto: { s: '−', cls: rojo },
  ingreso: { s: '+', cls: verde },
  transferencia: { s: '→', cls: 'text-muted' },
}

function Movimientos({
  transactions,
  accounts,
  categories,
  nombreCuenta,
  nombreCategoria,
  onCambio,
}: {
  transactions: Transaction[]
  accounts: Account[]
  categories: Category[]
  nombreCuenta: (id: string | null) => string
  nombreCategoria: (id: string | null) => string
  onCambio: () => void
}) {
  const [editando, setEditando] = useState<Transaction | null>(null)
  const eliminar = async (id: string) => {
    if (!window.confirm('¿Eliminar este movimiento? Se revertirá el saldo.')) return
    await api.deleteTransaction(id)
    onCambio()
  }
  return (
    <section className="space-y-3">
      {editando && (
        <EditorMovimiento
          tx={editando}
          accounts={accounts}
          categories={categories}
          onCerrar={() => setEditando(null)}
          onGuardado={() => {
            setEditando(null)
            onCambio()
          }}
        />
      )}
      <h3 className="eyebrow">Movimientos recientes</h3>
      {transactions.length === 0 ? (
        <p className="text-faint text-sm">Sin movimientos.</p>
      ) : (
        <ul className="card divide-y divide-[color:var(--c-line)] p-0 overflow-hidden">
          {transactions.slice(0, 20).map((t) => {
            const st = signoTipo[t.tipo]
            return (
              <li
                key={t.id}
                className="group flex items-center justify-between gap-3 px-4 py-2.5 text-sm"
              >
                <div className="min-w-0">
                  <span className={st.cls}>
                    {st.s} ${fmtMoney(t.monto)}
                  </span>
                  <span className="text-muted ml-2">
                    {t.tipo === 'transferencia'
                      ? `${nombreCuenta(t.account_id)} → ${nombreCuenta(t.cuenta_destino_id)}`
                      : `${nombreCategoria(t.category_id)} · ${nombreCuenta(t.account_id)}`}
                  </span>
                  {t.nota && <span className="text-faint ml-2 truncate">— {t.nota}</span>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-faint tabular-nums">{t.fecha}</span>
                  <button
                    onClick={() => setEditando(t)}
                    className="opacity-0 group-hover:opacity-100 text-faint hover:text-brand transition"
                    title="Editar"
                  >
                    ✎
                  </button>
                  <button
                    onClick={() => eliminar(t.id)}
                    className="opacity-0 group-hover:opacity-100 text-faint hover:text-[color:var(--c-danger)] transition"
                    title="Eliminar (revierte el saldo)"
                  >
                    ✕
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

// --- Presupuestos ---

function Presupuestos({
  budgets,
  categories,
  nombreCategoria,
  onCambio,
}: {
  budgets: BudgetProgress[]
  categories: Category[]
  nombreCategoria: (id: string | null) => string
  onCambio: () => void
}) {
  const [tope, setTope] = useState('')
  const [categoria, setCategoria] = useState('')

  const crear = async (e: FormEvent) => {
    e.preventDefault()
    if (!tope) return
    await api.createBudget(Number(tope), categoria || null)
    setTope('')
    onCambio()
  }
  const eliminar = async (id: string) => {
    if (!window.confirm('¿Eliminar este presupuesto?')) return
    await api.deleteBudget(id)
    onCambio()
  }

  return (
    <section className="space-y-3">
      <h3 className="eyebrow">Presupuestos del mes</h3>
      <div className="space-y-3">
        {budgets.map((b) => {
          const pct = Math.min(b.porcentaje, 100)
          const alerta = b.porcentaje >= 90
          return (
            <div key={b.id} className="group card p-4">
              <div className="flex items-center justify-between text-sm mb-2">
                <span>{nombreCategoria(b.category_id)}</span>
                <div className="flex items-center gap-3">
                  <span className="text-muted tabular-nums">
                    ${fmtMoney(b.gastado)} / ${fmtMoney(b.tope)} ({b.porcentaje}%)
                  </span>
                  <button
                    onClick={() => eliminar(b.id)}
                    className={`opacity-0 group-hover:opacity-100 text-faint hover:text-[color:var(--c-danger)] transition`}
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div className="h-2 rounded-full bg-[color:var(--c-surface-2)] overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${pct}%`,
                    background: alerta ? 'var(--c-danger)' : 'var(--c-teal)',
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
      <form onSubmit={crear} className="flex flex-wrap gap-2">
        <input
          value={tope}
          onChange={(e) => setTope(e.target.value)}
          type="number"
          placeholder="tope mensual"
          className="input w-40"
        />
        <select
          value={categoria}
          onChange={(e) => setCategoria(e.target.value)}
          className="input w-auto"
        >
          <option value="">Global (todo el mes)</option>
          {categories
            .filter((c) => c.activa)
            .map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
        </select>
        <button className="btn">Crear</button>
      </form>
    </section>
  )
}

// --- Detalle estilo libro contable (cuenta o categoría) ---

type Clasificacion = { lado: 'entrada' | 'salida'; etiqueta: string }

function DetalleLibro({
  titulo,
  subtitulo,
  saldoActual,
  exportBase,
  accounts,
  categories,
  onVolver,
  fetchTxs,
  clasificar,
}: {
  titulo: string
  subtitulo: string
  saldoActual?: string
  exportBase?: { accountId?: string; categoryId?: string }
  accounts: Account[]
  categories: Category[]
  onVolver: () => void
  fetchTxs: (desde: string, hasta: string) => Promise<Transaction[]>
  clasificar: (tx: Transaction) => Clasificacion | null
}) {
  const [desde, setDesde] = useState(inicioMes())
  const [hasta, setHasta] = useState(hoyStr())
  const [txs, setTxs] = useState<Transaction[]>([])
  const [cargando, setCargando] = useState(true)
  const [editando, setEditando] = useState<Transaction | null>(null)

  const recargar = useCallback(() => {
    setCargando(true)
    fetchTxs(desde, hasta)
      .then(setTxs)
      .finally(() => setCargando(false))
  }, [fetchTxs, desde, hasta])

  useEffect(() => {
    recargar()
  }, [recargar])

  const { salidas, entradas, totalS, totalE } = useMemo(() => {
    const salidas: { tx: Transaction; etiqueta: string }[] = []
    const entradas: { tx: Transaction; etiqueta: string }[] = []
    for (const tx of txs) {
      const c = clasificar(tx)
      if (!c) continue
      ;(c.lado === 'salida' ? salidas : entradas).push({ tx, etiqueta: c.etiqueta })
    }
    const totalS = salidas.reduce((s, e) => s + Number(e.tx.monto), 0)
    const totalE = entradas.reduce((s, e) => s + Number(e.tx.monto), 0)
    return { salidas, entradas, totalS, totalE }
  }, [txs, clasificar])

  const dif = totalE - totalS

  const eliminar = async (id: string) => {
    if (!window.confirm('¿Eliminar este movimiento? Se revertirá el saldo.')) return
    await api.deleteTransaction(id)
    recargar()
  }

  const preset = (d: string, h: string) => {
    setDesde(d)
    setHasta(h)
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {editando && (
        <EditorMovimiento
          tx={editando}
          accounts={accounts}
          categories={categories}
          onCerrar={() => setEditando(null)}
          onGuardado={() => {
            setEditando(null)
            recargar()
          }}
        />
      )}
      <button onClick={onVolver} className="text-muted hover:text-ink text-sm">
        ← Finanzas
      </button>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">{subtitulo}</p>
          <h2 className="font-serif text-3xl mt-1">{titulo}</h2>
          {saldoActual !== undefined && (
            <p className="text-sm text-muted mt-1">
              Saldo actual:{' '}
              <span className="text-ink font-medium">${fmtMoney(saldoActual)}</span>
            </p>
          )}
        </div>
        <div className="card px-5 py-3 text-right">
          <p className="eyebrow">Diferencia del período</p>
          <p className={`font-serif text-2xl ${dif >= 0 ? verde : rojo}`}>
            {dif >= 0 ? '+' : '−'}${fmtMoney(Math.abs(dif))}
          </p>
        </div>
      </div>

      {/* Rango de fechas */}
      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-muted flex items-center gap-2">
          Desde
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="input w-auto py-1.5"
          />
        </label>
        <label className="text-sm text-muted flex items-center gap-2">
          Hasta
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="input w-auto py-1.5"
          />
        </label>
        <div className="flex gap-1.5">
          <Preset label="Este mes" onClick={() => preset(inicioMes(), hoyStr())} />
          <Preset
            label="Mes pasado"
            onClick={() => {
              const d = new Date()
              preset(
                ymd(new Date(d.getFullYear(), d.getMonth() - 1, 1)),
                ymd(new Date(d.getFullYear(), d.getMonth(), 0))
              )
            }}
          />
          <Preset
            label="Este año"
            onClick={() => {
              const d = new Date()
              preset(ymd(new Date(d.getFullYear(), 0, 1)), hoyStr())
            }}
          />
          <Preset label="Todo" onClick={() => preset('', '')} />
        </div>
        <div className="ml-auto">
          <BotonExcel filtro={{ ...exportBase, desde, hasta }} label="Excel" />
        </div>
      </div>

      {cargando ? (
        <p className="text-faint">Cargando…</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          <Columna
            titulo="Salidas"
            colorTitulo={rojo}
            total={totalS}
            signo="−"
            items={salidas}
            onEliminar={eliminar}
            onEditar={setEditando}
          />
          <Columna
            titulo="Entradas"
            colorTitulo={verde}
            total={totalE}
            signo="+"
            items={entradas}
            onEliminar={eliminar}
            onEditar={setEditando}
          />
        </div>
      )}
    </div>
  )
}

function Preset({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="rounded-lg border border-line px-2.5 py-1.5 text-xs text-muted hover:text-ink hover:bg-surface transition"
    >
      {label}
    </button>
  )
}

function Columna({
  titulo,
  colorTitulo,
  total,
  signo,
  items,
  onEliminar,
  onEditar,
}: {
  titulo: string
  colorTitulo: string
  total: number
  signo: string
  items: { tx: Transaction; etiqueta: string }[]
  onEliminar: (id: string) => void
  onEditar: (tx: Transaction) => void
}) {
  return (
    <div className="card p-0 overflow-hidden">
      <div className="flex items-baseline justify-between px-4 py-3 border-b border-line">
        <span className={`eyebrow ${colorTitulo}`}>{titulo}</span>
        <span className={`font-medium tabular-nums ${colorTitulo}`}>
          {signo}${fmtMoney(total)}
        </span>
      </div>
      {items.length === 0 ? (
        <p className="text-faint text-sm px-4 py-6 text-center">Nada en el período.</p>
      ) : (
        <ul className="divide-y divide-[color:var(--c-line)]">
          {items.map(({ tx, etiqueta }) => (
            <li
              key={tx.id}
              className="group flex items-center justify-between gap-3 px-4 py-2.5 text-sm"
            >
              <div className="min-w-0">
                <div className="truncate">
                  <span className="font-medium">{etiqueta}</span>
                  {tx.nota && <span className="text-faint ml-2">— {tx.nota}</span>}
                </div>
                <div className="text-xs text-faint tabular-nums mt-0.5">{tx.fecha}</div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`tabular-nums ${colorTitulo}`}>
                  {signo}${fmtMoney(tx.monto)}
                </span>
                <button
                  onClick={() => onEditar(tx)}
                  className="opacity-0 group-hover:opacity-100 text-faint hover:text-brand transition"
                  title="Editar"
                >
                  ✎
                </button>
                <button
                  onClick={() => onEliminar(tx.id)}
                  className="opacity-0 group-hover:opacity-100 text-faint hover:text-[color:var(--c-danger)] transition"
                  title="Eliminar (revierte el saldo)"
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
