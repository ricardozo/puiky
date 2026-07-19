import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type MarketProduct } from '../api'

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
