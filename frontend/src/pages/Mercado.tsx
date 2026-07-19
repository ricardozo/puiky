import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type MarketProduct } from '../api'

const UNIDADES = ['unidad', 'g', 'kg', 'ml', 'l']

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
    partes.push(
      d === 0 ? 'comprado hoy' : `último hace ${d} día${d === 1 ? '' : 's'}`
    )
  } else {
    partes.push('sin compras aún')
  }
  return partes.join(' · ')
}

export default function Mercado() {
  const [productos, setProductos] = useState<MarketProduct[]>([])
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback(
    () => api.listMarketProducts().then(setProductos).finally(() => setCargando(false)),
    []
  )
  useEffect(() => {
    cargar()
  }, [cargar])

  const comprar = async (p: MarketProduct) => {
    await api.registrarCompra(p.id)
    cargar()
  }
  const eliminar = async (p: MarketProduct) => {
    if (!window.confirm(`¿Eliminar "${p.nombre}" y su historial de compras?`)) return
    await api.deleteMarketProduct(p.id)
    cargar()
  }
  const cambiarCadencia = async (p: MarketProduct, dias: number | null) => {
    await api.updateMarketProduct(p.id, { cadencia_dias: dias })
    cargar()
  }

  const porComprar = productos.filter((p) => p.por_comprar)

  return (
    <div className="space-y-8 max-w-3xl">
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
                    <button onClick={() => comprar(p)} className="btn-gold btn text-sm py-1.5 shrink-0">
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
                      <div className="flex items-center gap-2 shrink-0">
                        <label className="text-xs text-faint flex items-center gap-1">
                          cada
                          <input
                            type="number"
                            min={1}
                            defaultValue={p.cadencia_dias ?? ''}
                            onBlur={(ev) =>
                              cambiarCadencia(p, ev.target.value ? Number(ev.target.value) : null)
                            }
                            placeholder="—"
                            className="input w-14 py-1 text-center"
                            title="Días entre compras"
                          />
                          d
                        </label>
                        <button
                          onClick={() => comprar(p)}
                          className="btn-ghost btn text-sm py-1"
                          title="Registrar compra (reinicia el ciclo)"
                        >
                          ✓
                        </button>
                        <button
                          onClick={() => eliminar(p)}
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
          </section>
        </>
      )}
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
