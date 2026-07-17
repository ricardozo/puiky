import { useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  api,
  ApiError,
  fmtMoney,
  type Account,
  type BudgetProgress,
  type Category,
  type Transaction,
} from '../api'

const inputCls =
  'rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 outline-none focus:border-indigo-500'

export default function Finanzas() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [budgets, setBudgets] = useState<BudgetProgress[]>([])
  const [cargando, setCargando] = useState(true)

  const cargar = async () => {
    const [acc, cats, txs, buds] = await Promise.all([
      api.listAccounts(),
      api.listCategories(),
      api.listTransactions(),
      api.listBudgets(),
    ])
    const prog = await Promise.all(buds.map((b) => api.budgetProgress(b.id)))
    setAccounts(acc)
    setCategories(cats)
    setTransactions(txs)
    setBudgets(prog)
    setCargando(false)
  }

  useEffect(() => {
    cargar()
  }, [])

  const nombreCuenta = (id: string | null) =>
    accounts.find((a) => a.id === id)?.nombre ?? '—'
  const nombreCategoria = (id: string | null) =>
    id ? categories.find((c) => c.id === id)?.nombre ?? '—' : 'Global'

  const total = useMemo(
    () => accounts.reduce((s, a) => s + Number(a.saldo), 0),
    [accounts]
  )

  if (cargando) return <p className="text-slate-500">Cargando…</p>

  return (
    <div className="space-y-8 max-w-4xl">
      <h2 className="text-xl font-semibold">Finanzas</h2>

      <Cuentas accounts={accounts} total={total} onCambio={cargar} />
      <Movimiento
        accounts={accounts}
        categories={categories}
        onCambio={cargar}
      />
      <Movimientos
        transactions={transactions}
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

function Cuentas({
  accounts,
  total,
  onCambio,
}: {
  accounts: Account[]
  total: number
  onCambio: () => void
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
        <h3 className="font-medium">Cuentas</h3>
        <span className="text-sm text-slate-400">
          Total: <span className="text-slate-100">${fmtMoney(total)}</span>
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        {accounts.map((a) => (
          <div
            key={a.id}
            className="rounded-xl border border-slate-800 bg-slate-900/50 p-4"
          >
            <div className="text-sm text-slate-400">{a.nombre}</div>
            <div className="text-lg font-semibold">${fmtMoney(a.saldo)}</div>
            <div className="text-xs text-slate-500 mt-1">{a.tipo}</div>
          </div>
        ))}
      </div>
      <form onSubmit={crear} className="flex flex-wrap gap-2">
        <input
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Nueva cuenta"
          className={inputCls}
        />
        <input
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          placeholder="tipo (efectivo/banco/…)"
          className={inputCls}
        />
        <input
          value={saldo}
          onChange={(e) => setSaldo(e.target.value)}
          type="number"
          placeholder="saldo inicial"
          className={`${inputCls} w-36`}
        />
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Añadir
        </button>
      </form>
    </section>
  )
}

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
      <h3 className="font-medium">Registrar movimiento</h3>
      <form onSubmit={registrar} className="flex flex-wrap items-center gap-2">
        <select
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          className={inputCls}
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
          className={`${inputCls} w-32`}
        />
        <select
          value={cuenta}
          onChange={(e) => setCuenta(e.target.value)}
          className={inputCls}
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
            className={inputCls}
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
            className={inputCls}
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
          className={`${inputCls} flex-1 min-w-40`}
        />
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Registrar
        </button>
      </form>
      {error && <p className="text-red-400 text-sm">{error}</p>}
    </section>
  )
}

const colorTipo: Record<string, string> = {
  gasto: 'text-red-400',
  ingreso: 'text-emerald-400',
  transferencia: 'text-slate-400',
}

function Movimientos({
  transactions,
  nombreCuenta,
  nombreCategoria,
  onCambio,
}: {
  transactions: Transaction[]
  nombreCuenta: (id: string | null) => string
  nombreCategoria: (id: string | null) => string
  onCambio: () => void
}) {
  const eliminar = async (id: string) => {
    await api.deleteTransaction(id)
    onCambio()
  }
  return (
    <section className="space-y-3">
      <h3 className="font-medium">Movimientos recientes</h3>
      {transactions.length === 0 ? (
        <p className="text-slate-500 text-sm">Sin movimientos.</p>
      ) : (
        <ul className="divide-y divide-slate-800 rounded-xl border border-slate-800">
          {transactions.slice(0, 20).map((t) => (
            <li
              key={t.id}
              className="group flex items-center justify-between gap-3 px-4 py-2.5 text-sm"
            >
              <div className="min-w-0">
                <span className={colorTipo[t.tipo]}>
                  {t.tipo === 'gasto' ? '−' : t.tipo === 'ingreso' ? '+' : '→'} $
                  {fmtMoney(t.monto)}
                </span>
                <span className="text-slate-400 ml-2">
                  {t.tipo === 'transferencia'
                    ? `${nombreCuenta(t.account_id)} → ${nombreCuenta(t.cuenta_destino_id)}`
                    : `${nombreCategoria(t.category_id)} · ${nombreCuenta(t.account_id)}`}
                </span>
                {t.nota && (
                  <span className="text-slate-500 ml-2 truncate">— {t.nota}</span>
                )}
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs text-slate-500">{t.fecha}</span>
                <button
                  onClick={() => eliminar(t.id)}
                  className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition"
                  title="Eliminar (revierte el saldo)"
                >
                  ✕
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

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
    await api.deleteBudget(id)
    onCambio()
  }

  return (
    <section className="space-y-3">
      <h3 className="font-medium">Presupuestos del mes</h3>
      <div className="space-y-3">
        {budgets.map((b) => {
          const pct = Math.min(b.porcentaje, 100)
          const alerta = b.porcentaje >= 90
          return (
            <div
              key={b.id}
              className="group rounded-xl border border-slate-800 bg-slate-900/50 p-4"
            >
              <div className="flex items-center justify-between text-sm mb-2">
                <span>{nombreCategoria(b.category_id)}</span>
                <div className="flex items-center gap-3">
                  <span className="text-slate-400">
                    ${fmtMoney(b.gastado)} / ${fmtMoney(b.tope)} ({b.porcentaje}%)
                  </span>
                  <button
                    onClick={() => eliminar(b.id)}
                    className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div className="h-2 rounded bg-slate-800 overflow-hidden">
                <div
                  className={`h-full ${alerta ? 'bg-red-500' : 'bg-indigo-500'}`}
                  style={{ width: `${pct}%` }}
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
          className={`${inputCls} w-40`}
        />
        <select
          value={categoria}
          onChange={(e) => setCategoria(e.target.value)}
          className={inputCls}
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
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Crear
        </button>
      </form>
    </section>
  )
}
