import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Portfolio, type Project } from '../api'

const inputCls =
  'rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 outline-none focus:border-indigo-500'

type Seleccion =
  | { tipo: 'home' }
  | { tipo: 'todos' }
  | { tipo: 'sin' }
  | { tipo: 'portafolio'; pf: Portfolio }

export default function Projects() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [sel, setSel] = useState<Seleccion>({ tipo: 'home' })

  const cargarPortfolios = useCallback(
    () => api.listPortfolios().then(setPortfolios),
    []
  )
  useEffect(() => {
    cargarPortfolios()
  }, [cargarPortfolios])

  if (sel.tipo === 'home')
    return (
      <Home portfolios={portfolios} onAbrir={setSel} onCambio={cargarPortfolios} />
    )

  return (
    <Detalle
      sel={sel}
      portfolios={portfolios}
      onVolver={() => {
        cargarPortfolios()
        setSel({ tipo: 'home' })
      }}
    />
  )
}

function Home({
  portfolios,
  onAbrir,
  onCambio,
}: {
  portfolios: Portfolio[]
  onAbrir: (s: Seleccion) => void
  onCambio: () => void
}) {
  const [nuevo, setNuevo] = useState('')
  const crear = async (e: FormEvent) => {
    e.preventDefault()
    if (!nuevo.trim()) return
    await api.createPortfolio(nuevo.trim())
    setNuevo('')
    onCambio()
  }
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Proyectos</h2>
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <button
          onClick={() => onAbrir({ tipo: 'todos' })}
          className="text-left rounded-xl border border-slate-800 bg-slate-800/40 p-4 hover:border-slate-600 transition"
        >
          <div className="text-2xl">🗂️</div>
          <div className="font-medium mt-2">Todos los proyectos</div>
        </button>
        <button
          onClick={() => onAbrir({ tipo: 'sin' })}
          className="text-left rounded-xl border border-slate-800 bg-slate-800/40 p-4 hover:border-slate-600 transition"
        >
          <div className="text-2xl">🗂️</div>
          <div className="font-medium mt-2">Sin portafolio</div>
        </button>
        {portfolios.map((pf) => (
          <button
            key={pf.id}
            onClick={() => onAbrir({ tipo: 'portafolio', pf })}
            className="text-left rounded-xl border border-slate-800 bg-slate-900/50 p-4 hover:border-slate-600 transition"
          >
            <div className="text-2xl">💼</div>
            <div className="font-medium mt-2">{pf.nombre}</div>
            <div className="text-xs text-slate-500 mt-1">
              {pf.proyectos} proyecto{pf.proyectos === 1 ? '' : 's'}
            </div>
          </button>
        ))}
      </div>
      <form onSubmit={crear} className="flex gap-2 max-w-md">
        <input
          value={nuevo}
          onChange={(e) => setNuevo(e.target.value)}
          placeholder="Nuevo portafolio…"
          className={`${inputCls} flex-1`}
        />
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Crear
        </button>
      </form>
    </div>
  )
}

const colorEstado: Record<string, string> = {
  activo: 'bg-emerald-600/30 text-emerald-300',
  pausado: 'bg-amber-600/30 text-amber-300',
  terminado: 'bg-slate-700 text-slate-400',
}

function Detalle({
  sel,
  portfolios,
  onVolver,
}: {
  sel: Seleccion
  portfolios: Portfolio[]
  onVolver: () => void
}) {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [nuevo, setNuevo] = useState('')
  const [cargando, setCargando] = useState(true)

  const pfId = sel.tipo === 'portafolio' ? sel.pf.id : null
  const titulo =
    sel.tipo === 'portafolio'
      ? sel.pf.nombre
      : sel.tipo === 'sin'
        ? 'Sin portafolio'
        : 'Todos los proyectos'

  const cargar = useCallback(() => {
    const opts =
      sel.tipo === 'portafolio'
        ? { portfolioId: sel.pf.id }
        : sel.tipo === 'sin'
          ? { sinPortafolio: true }
          : undefined
    api.listProjects(opts).then(setProjects).finally(() => setCargando(false))
  }, [sel])

  useEffect(() => {
    cargar()
  }, [cargar])

  const crear = async (e: FormEvent) => {
    e.preventDefault()
    if (!nuevo.trim()) return
    await api.createProject(nuevo.trim(), pfId)
    setNuevo('')
    cargar()
  }
  const mover = async (id: string, destino: string) => {
    await api.moveProject(id, destino || null)
    cargar()
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <button onClick={onVolver} className="text-slate-400 hover:text-slate-200 text-sm">
          ← Portafolios
        </button>
        <h2 className="text-xl font-semibold">💼 {titulo}</h2>
      </div>

      <form onSubmit={crear} className="flex gap-2 max-w-xl">
        <input
          value={nuevo}
          onChange={(e) => setNuevo(e.target.value)}
          placeholder={
            sel.tipo === 'portafolio'
              ? `Nuevo proyecto en ${sel.pf.nombre}…`
              : 'Nuevo proyecto…'
          }
          className={`${inputCls} flex-1`}
        />
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Crear
        </button>
      </form>

      {cargando ? (
        <p className="text-slate-500">Cargando…</p>
      ) : projects.length === 0 ? (
        <p className="text-slate-500">Sin proyectos aquí.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <div
              key={p.id}
              onClick={() => navigate(`/proyectos/${p.id}`)}
              className="group cursor-pointer rounded-xl border border-slate-800 bg-slate-900/50 p-4 hover:border-slate-600 transition"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="font-medium">{p.nombre}</div>
                <span
                  className={`shrink-0 rounded px-2 py-0.5 text-xs ${
                    colorEstado[p.estado] ?? 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {p.estado}
                </span>
              </div>
              <select
                value={p.portfolio_id ?? ''}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => {
                  e.stopPropagation()
                  mover(p.id, e.target.value)
                }}
                className="opacity-0 group-hover:opacity-100 mt-3 rounded bg-slate-900 border border-slate-700 text-xs px-1.5 py-1 transition"
                title="Mover a portafolio"
              >
                <option value="">— sin portafolio —</option>
                {portfolios.map((pf) => (
                  <option key={pf.id} value={pf.id}>
                    {pf.nombre}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
