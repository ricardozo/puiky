import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type Account, type MarketProduct, type Trip, type TripItem } from '../api'

const UNIDADES = ['unidad', 'g', 'kg', 'ml', 'l']

function hoyStr(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

function estado(p: MarketProduct): { texto: string; clase: string } {
  if (!p.cadencia_dias) return { texto: 'sin ciclo', clase: 'pill-mute' }
  if (p.por_comprar) return { texto: 'por comprar', clase: 'pill-warn' }
  return { texto: 'al día', clase: 'pill-ok' }
}

function subtitulo(p: MarketProduct): string {
  const partes: string[] = []
  if (p.cadencia_dias) partes.push(`cada ${p.cadencia_dias} días`)
  if (p.ultima_compra) {
    const d = p.dias_desde
    partes.push(d === 0 ? 'comprado hoy' : `último hace ${d} día${d === 1 ? '' : 's'}`)
  } else {
    partes.push('sin compras aún')
  }
  return partes.join(' · ')
}

export default function Mercado() {
  const [productos, setProductos] = useState<MarketProduct[]>([])
  const [cargando, setCargando] = useState(true)
  const [comprando, setComprando] = useState<MarketProduct | null>(null)
  const [editando, setEditando] = useState<MarketProduct | null>(null)

  const cargar = useCallback(
    () => api.listMarketProducts().then(setProductos).finally(() => setCargando(false)),
    []
  )
  useEffect(() => {
    cargar()
  }, [cargar])

  const eliminar = async (p: MarketProduct) => {
    if (!window.confirm(`¿Eliminar "${p.nombre}" y su historial de compras?`)) return
    await api.deleteMarketProduct(p.id)
    cargar()
  }

  const porComprar = productos.filter((p) => p.por_comprar)

  return (
    <div className="space-y-8 max-w-3xl">
      {comprando && (
        <CompraModal
          producto={comprando}
          onCerrar={() => setComprando(null)}
          onGuardado={() => {
            setComprando(null)
            cargar()
          }}
        />
      )}
      {editando && (
        <EditorProducto
          producto={editando}
          onCerrar={() => setEditando(null)}
          onGuardado={() => {
            setEditando(null)
            cargar()
          }}
        />
      )}

      <div>
        <h2 className="font-serif text-2xl">Mercado</h2>
        <p className="text-sm text-muted mt-1">
          Tus productos recurrentes. Marca cuando compras y Puiky te avisa cuándo reponer.
        </p>
      </div>

      <CompraEnCurso onCerrada={cargar} />

      <NuevoProductoForm onCreado={cargar} />

      {cargando ? (
        <p className="text-faint">Cargando…</p>
      ) : (
        <>
          {porComprar.length > 0 && (
            <section className="space-y-3">
              <h3 className="eyebrow text-brand">Por comprar</h3>
              <div className="grid gap-2 sm:grid-cols-2">
                {porComprar.map((p) => (
                  <div
                    key={p.id}
                    className="card p-4 flex items-center justify-between gap-3 border-[color:var(--c-brand)]"
                  >
                    <div className="min-w-0">
                      <div className="font-medium truncate">{p.nombre}</div>
                      <div className="text-xs text-muted mt-0.5">{subtitulo(p)}</div>
                    </div>
                    <button
                      onClick={() => setComprando(p)}
                      className="btn-gold btn text-sm py-1.5 shrink-0"
                    >
                      ✓ Comprado
                    </button>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="space-y-3">
            <h3 className="eyebrow">Todos los productos</h3>
            {productos.length === 0 ? (
              <p className="text-faint text-sm">
                Aún no hay productos. Agrega el primero arriba.
              </p>
            ) : (
              <ul className="card divide-y divide-[color:var(--c-line)] p-0 overflow-hidden">
                {productos.map((p) => {
                  const e = estado(p)
                  return (
                    <li
                      key={p.id}
                      className="group flex items-center justify-between gap-3 px-4 py-3"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium truncate">{p.nombre}</span>
                          <span className={`pill shrink-0 ${e.clase}`}>{e.texto}</span>
                        </div>
                        <div className="text-xs text-faint mt-0.5">{subtitulo(p)}</div>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <button
                          onClick={() => setComprando(p)}
                          className="btn-ghost btn text-sm py-1"
                          title="Registrar compra"
                        >
                          ✓ Comprado
                        </button>
                        <button
                          onClick={() => setEditando(p)}
                          className="text-faint hover:text-brand transition px-1"
                          title="Editar"
                        >
                          ✎
                        </button>
                        <button
                          onClick={() => eliminar(p)}
                          className="opacity-0 group-hover:opacity-100 text-faint hover:text-[color:var(--c-danger)] transition px-1"
                          title="Eliminar"
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
        </>
      )}
    </div>
  )
}

function CompraModal({
  producto,
  onCerrar,
  onGuardado,
}: {
  producto: MarketProduct
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [cantidad, setCantidad] = useState('1')
  const [precio, setPrecio] = useState('')
  const [fecha, setFecha] = useState(hoyStr())
  const [busy, setBusy] = useState(false)

  const guardar = async () => {
    setBusy(true)
    try {
      await api.registrarCompra(producto.id, {
        cantidad: Number(cantidad) || 1,
        precio: precio ? Number(precio) : null,
        fecha,
      })
      onGuardado()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4"
      onClick={onCerrar}
    >
      <div className="card w-full max-w-sm p-6 space-y-4" onClick={(ev) => ev.stopPropagation()}>
        <h3 className="font-serif text-xl">Registrar compra</h3>
        <p className="text-sm text-muted">{producto.nombre}</p>

        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs text-muted flex flex-col gap-1">
            Cantidad ({producto.unidad})
            <input
              type="number"
              value={cantidad}
              onChange={(ev) => setCantidad(ev.target.value)}
              className="input"
            />
          </label>
          <label className="text-xs text-muted flex flex-col gap-1">
            Precio (opcional)
            <input
              type="number"
              value={precio}
              onChange={(ev) => setPrecio(ev.target.value)}
              placeholder="—"
              className="input"
            />
          </label>
        </div>
        <label className="text-xs text-muted flex flex-col gap-1">
          Fecha
          <input
            type="date"
            value={fecha}
            onChange={(ev) => setFecha(ev.target.value)}
            className="input"
          />
        </label>

        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onCerrar} className="btn-ghost btn">
            Cancelar
          </button>
          <button onClick={guardar} disabled={busy} className="btn">
            {busy ? 'Guardando…' : 'Registrar'}
          </button>
        </div>
      </div>
    </div>
  )
}

function EditorProducto({
  producto,
  onCerrar,
  onGuardado,
}: {
  producto: MarketProduct
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [nombre, setNombre] = useState(producto.nombre)
  const [unidad, setUnidad] = useState(producto.unidad)
  const [cadencia, setCadencia] = useState(producto.cadencia_dias?.toString() ?? '')
  const [notas, setNotas] = useState(producto.notas ?? '')
  const [activo, setActivo] = useState(producto.activo)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const guardar = async () => {
    if (!nombre.trim()) return
    setBusy(true)
    setError('')
    try {
      await api.updateMarketProduct(producto.id, {
        nombre: nombre.trim(),
        unidad,
        cadencia_dias: cadencia ? Number(cadencia) : null,
        notas: notas.trim() || null,
        activo,
      })
      onGuardado()
    } catch {
      setError('No se pudo guardar (¿nombre repetido?)')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4"
      onClick={onCerrar}
    >
      <div className="card w-full max-w-sm p-6 space-y-4" onClick={(ev) => ev.stopPropagation()}>
        <h3 className="font-serif text-xl">Editar producto</h3>

        <label className="text-xs text-muted flex flex-col gap-1">
          Nombre
          <input value={nombre} onChange={(ev) => setNombre(ev.target.value)} className="input" />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs text-muted flex flex-col gap-1">
            Unidad
            <select value={unidad} onChange={(ev) => setUnidad(ev.target.value)} className="input">
              {UNIDADES.map((u) => (
                <option key={u} value={u}>
                  {u}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-muted flex flex-col gap-1">
            Cada … días
            <input
              type="number"
              min={1}
              value={cadencia}
              onChange={(ev) => setCadencia(ev.target.value)}
              placeholder="sin ciclo"
              className="input"
            />
          </label>
        </div>
        <label className="text-xs text-muted flex flex-col gap-1">
          Notas
          <input
            value={notas}
            onChange={(ev) => setNotas(ev.target.value)}
            placeholder="opcional"
            className="input"
          />
        </label>
        <label className="text-sm text-muted flex items-center gap-2">
          <input
            type="checkbox"
            checked={activo}
            onChange={(ev) => setActivo(ev.target.checked)}
            className="accent-[color:var(--c-teal)]"
          />
          Activo
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

function NuevoProductoForm({ onCreado }: { onCreado: () => void }) {
  const [nombre, setNombre] = useState('')
  const [cadencia, setCadencia] = useState('')
  const [unidad, setUnidad] = useState('unidad')

  const crear = async (e: FormEvent) => {
    e.preventDefault()
    if (!nombre.trim()) return
    await api.createMarketProduct({
      nombre: nombre.trim(),
      unidad,
      cadencia_dias: cadencia ? Number(cadencia) : null,
    })
    setNombre('')
    setCadencia('')
    onCreado()
  }

  return (
    <form onSubmit={crear} className="flex flex-wrap items-end gap-2">
      <input
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
        placeholder="Nuevo producto (ej. Jabón de lavadora)"
        className="input flex-1 min-w-48"
      />
      <select value={unidad} onChange={(e) => setUnidad(e.target.value)} className="input w-auto">
        {UNIDADES.map((u) => (
          <option key={u} value={u}>
            {u}
          </option>
        ))}
      </select>
      <input
        value={cadencia}
        onChange={(e) => setCadencia(e.target.value)}
        type="number"
        min={1}
        placeholder="cada … días"
        className="input w-32"
      />
      <button className="btn">Agregar</button>
    </form>
  )
}

function fmt(v: string | number | null): string {
  if (v === null || v === '') return '0'
  return Number(v).toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

function CompraEnCurso({ onCerrada }: { onCerrada: () => void }) {
  const [trip, setTrip] = useState<Trip | null>(null)
  const [cargando, setCargando] = useState(true)
  const [nuevo, setNuevo] = useState('')
  const [item, setItem] = useState<TripItem | null>(null)
  const [cerrando, setCerrando] = useState(false)

  const cargar = useCallback(
    () => api.compraEnCurso().then(setTrip).finally(() => setCargando(false)),
    []
  )
  useEffect(() => {
    cargar()
  }, [cargar])

  const iniciar = async () => setTrip(await api.iniciarCompra())
  const sugerir = async () => {
    if (trip) setTrip(await api.sugerirCompra(trip.id))
  }
  const agregar = async (e: FormEvent) => {
    e.preventDefault()
    if (!trip || !nuevo.trim()) return
    await api.addTripItem(trip.id, { nombre: nuevo.trim() })
    setNuevo('')
    cargar()
  }
  const quitar = async (it: TripItem) => {
    await api.removeTripItem(it.id)
    cargar()
  }
  const desmarcar = async (it: TripItem) => {
    await api.updateTripItem(it.id, { comprado: false })
    cargar()
  }

  if (cargando) return null

  if (!trip) {
    return (
      <div className="card p-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="font-medium">¿Vas al súper?</div>
          <div className="text-xs text-muted mt-0.5">
            Arma tu lista y ve marcando lo que compras.
          </div>
        </div>
        <button onClick={iniciar} className="btn">
          🛒 Iniciar compra
        </button>
      </div>
    )
  }

  const total = trip.items
    .filter((i) => i.comprado)
    .reduce((s, i) => s + Number(i.precio || 0), 0)
  const faltan = trip.items.filter((i) => !i.comprado).length

  return (
    <section className="card p-5 space-y-4 border-[color:var(--c-brand)]">
      {item && (
        <ItemModal
          item={item}
          onCerrar={() => setItem(null)}
          onGuardado={() => {
            setItem(null)
            cargar()
          }}
        />
      )}
      {cerrando && (
        <CerrarModal
          trip={trip}
          onCerrar={() => setCerrando(false)}
          onCerrada={() => {
            setCerrando(false)
            setTrip(null)
            onCerrada()
          }}
        />
      )}

      <div className="flex items-center justify-between gap-3">
        <h3 className="eyebrow text-brand">Compra en curso</h3>
        <span className="text-sm text-muted">
          {faltan} por comprar ·{' '}
          <span className="text-ink font-medium">${fmt(total)}</span> en el carrito
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        <form onSubmit={agregar} className="flex gap-2 flex-1 min-w-48">
          <input
            value={nuevo}
            onChange={(e) => setNuevo(e.target.value)}
            placeholder="Agregar a la lista…"
            className="input flex-1"
          />
          <button className="btn-ghost btn">+</button>
        </form>
        <button onClick={sugerir} className="btn-ghost btn text-sm" title="Agregar lo que toca reponer">
          ✨ Sugerir
        </button>
      </div>

      {trip.items.length === 0 ? (
        <p className="text-faint text-sm">
          Lista vacía. Agrega productos o toca «Sugerir».
        </p>
      ) : (
        <ul className="divide-y divide-[color:var(--c-line)]">
          {trip.items.map((it) => (
            <li key={it.id} className="group flex items-center gap-3 py-2.5">
              <button
                onClick={() => (it.comprado ? desmarcar(it) : setItem(it))}
                className={`size-6 rounded-full border flex items-center justify-center shrink-0 text-sm ${
                  it.comprado
                    ? 'bg-[color:var(--c-green)] border-transparent text-white'
                    : 'border-line text-transparent hover:border-teal'
                }`}
                title={it.comprado ? 'Comprado (clic para desmarcar)' : 'Marcar comprado'}
              >
                ✓
              </button>
              <div className="min-w-0 flex-1">
                <div className={`truncate ${it.comprado ? 'text-muted' : ''}`}>
                  {it.nombre}
                </div>
                {it.comprado && (it.precio || it.tamano) && (
                  <div className="text-xs text-faint">
                    {it.tamano}
                    {it.tamano && it.precio ? ' · ' : ''}
                    {it.precio ? `$${fmt(it.precio)}` : ''}
                  </div>
                )}
              </div>
              {!it.comprado && (
                <button onClick={() => setItem(it)} className="btn-ghost btn text-sm py-1">
                  ✓ Comprar
                </button>
              )}
              <button
                onClick={() => quitar(it)}
                className="opacity-0 group-hover:opacity-100 text-faint hover:text-[color:var(--c-danger)] transition px-1"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex justify-end pt-1">
        <button onClick={() => setCerrando(true)} className="btn-gold btn">
          Cerrar compra
        </button>
      </div>
    </section>
  )
}

function ItemModal({
  item,
  onCerrar,
  onGuardado,
}: {
  item: TripItem
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [cantidad, setCantidad] = useState(item.cantidad ? String(Number(item.cantidad)) : '1')
  const [tamano, setTamano] = useState(item.tamano ?? '')
  const [precio, setPrecio] = useState(item.precio ? String(Number(item.precio)) : '')
  const [busy, setBusy] = useState(false)

  const guardar = async () => {
    setBusy(true)
    try {
      await api.updateTripItem(item.id, {
        comprado: true,
        cantidad: Number(cantidad) || 1,
        tamano: tamano.trim() || null,
        precio: precio ? Number(precio) : null,
      })
      onGuardado()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4" onClick={onCerrar}>
      <div className="card w-full max-w-sm p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-serif text-xl">Comprar</h3>
        <p className="text-sm text-muted">{item.nombre}</p>
        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs text-muted flex flex-col gap-1">
            Cantidad
            <input type="number" value={cantidad} onChange={(e) => setCantidad(e.target.value)} className="input" />
          </label>
          <label className="text-xs text-muted flex flex-col gap-1">
            Tamaño
            <input value={tamano} onChange={(e) => setTamano(e.target.value)} placeholder="2 L, 500 g…" className="input" />
          </label>
        </div>
        <label className="text-xs text-muted flex flex-col gap-1">
          Precio (opcional)
          <input type="number" value={precio} onChange={(e) => setPrecio(e.target.value)} placeholder="—" className="input" />
        </label>
        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onCerrar} className="btn-ghost btn">
            Cancelar
          </button>
          <button onClick={guardar} disabled={busy} className="btn">
            {busy ? 'Guardando…' : '✓ Comprado'}
          </button>
        </div>
      </div>
    </div>
  )
}

function CerrarModal({
  trip,
  onCerrar,
  onCerrada,
}: {
  trip: Trip
  onCerrar: () => void
  onCerrada: () => void
}) {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [cuenta, setCuenta] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.listAccounts().then(setAccounts)
  }, [])

  const total = trip.items
    .filter((i) => i.comprado)
    .reduce((s, i) => s + Number(i.precio || 0), 0)

  const cerrar = async () => {
    setBusy(true)
    try {
      await api.cerrarCompra(trip.id, { account_id: cuenta || null, categoria: 'Mercado' })
      onCerrada()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4" onClick={onCerrar}>
      <div className="card w-full max-w-sm p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="font-serif text-xl">Cerrar compra</h3>
        <p className="text-sm text-muted">
          Total del carrito:{' '}
          <span className="text-ink font-medium">${fmt(total)}</span>
        </p>
        <label className="text-xs text-muted flex flex-col gap-1">
          Cargar el gasto a
          <select value={cuenta} onChange={(e) => setCuenta(e.target.value)} className="input">
            <option value="">No registrar gasto</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.nombre}
              </option>
            ))}
          </select>
        </label>
        <p className="text-xs text-faint">
          Se guardan las compras del catálogo y (si eliges cuenta) el gasto en finanzas.
        </p>
        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onCerrar} className="btn-ghost btn">
            Cancelar
          </button>
          <button onClick={cerrar} disabled={busy} className="btn-gold btn">
            {busy ? 'Cerrando…' : 'Cerrar compra'}
          </button>
        </div>
      </div>
    </div>
  )
}
