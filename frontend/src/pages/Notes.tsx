import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  api,
  type Note,
  type Notebook,
  type SearchResult,
} from '../api'

const inputCls =
  'rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 outline-none focus:border-indigo-500'

type Seleccion =
  | { tipo: 'home' }
  | { tipo: 'todas' }
  | { tipo: 'sin' }
  | { tipo: 'cuaderno'; nb: Notebook }

export default function Notes() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([])
  const [sel, setSel] = useState<Seleccion>({ tipo: 'home' })

  const cargarNotebooks = useCallback(
    () => api.listNotebooks().then(setNotebooks),
    []
  )
  useEffect(() => {
    cargarNotebooks()
  }, [cargarNotebooks])

  const nombreCuaderno = (id: string | null) =>
    id ? notebooks.find((n) => n.id === id)?.nombre ?? '—' : null

  if (sel.tipo === 'home')
    return (
      <Home
        notebooks={notebooks}
        nombreCuaderno={nombreCuaderno}
        onAbrir={setSel}
        onCambio={cargarNotebooks}
      />
    )

  return (
    <Detalle
      sel={sel}
      notebooks={notebooks}
      nombreCuaderno={nombreCuaderno}
      onVolver={() => {
        cargarNotebooks()
        setSel({ tipo: 'home' })
      }}
    />
  )
}

function Home({
  notebooks,
  nombreCuaderno,
  onAbrir,
  onCambio,
}: {
  notebooks: Notebook[]
  nombreCuaderno: (id: string | null) => string | null
  onAbrir: (s: Seleccion) => void
  onCambio: () => void
}) {
  const [query, setQuery] = useState('')
  const [resultados, setResultados] = useState<SearchResult[] | null>(null)
  const [nuevoNb, setNuevoNb] = useState('')

  const buscar = async (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) {
      setResultados(null)
      return
    }
    setResultados(await api.searchNotes(query.trim()))
  }
  const crearNb = async (e: FormEvent) => {
    e.preventDefault()
    if (!nuevoNb.trim()) return
    await api.createNotebook(nuevoNb.trim())
    setNuevoNb('')
    onCambio()
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Notas</h2>

      <form onSubmit={buscar} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Búsqueda semántica en todos los cuadernos…"
          className={`${inputCls} flex-1`}
        />
        <button className="rounded-lg border border-slate-700 px-4 hover:bg-slate-800">
          Buscar
        </button>
        {resultados && (
          <button
            type="button"
            onClick={() => {
              setResultados(null)
              setQuery('')
            }}
            className="rounded-lg border border-slate-700 px-4 hover:bg-slate-800"
          >
            Limpiar
          </button>
        )}
      </form>

      {resultados ? (
        <div className="space-y-2">
          <p className="text-sm text-slate-400">
            {resultados.length} resultado(s) por significado
          </p>
          {resultados.map((n) => (
            <div
              key={n.id}
              className="rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-3"
            >
              <p className="whitespace-pre-wrap">{n.contenido}</p>
              <p className="text-xs text-slate-500 mt-1">
                <span className="text-indigo-400">
                  {(n.similitud * 100).toFixed(0)}% afín
                </span>
                {nombreCuaderno(n.notebook_id) && (
                  <span className="ml-2">📓 {nombreCuaderno(n.notebook_id)}</span>
                )}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <SpecialCard
              titulo="Todas las notas"
              onClick={() => onAbrir({ tipo: 'todas' })}
            />
            <SpecialCard
              titulo="Sin cuaderno"
              onClick={() => onAbrir({ tipo: 'sin' })}
            />
            {notebooks.map((nb) => (
              <button
                key={nb.id}
                onClick={() => onAbrir({ tipo: 'cuaderno', nb })}
                className="text-left rounded-xl border border-slate-800 bg-slate-900/50 p-4 hover:border-slate-600 transition"
              >
                <div className="text-2xl">📓</div>
                <div className="font-medium mt-2">{nb.nombre}</div>
                <div className="text-xs text-slate-500 mt-1">
                  {nb.notas} nota{nb.notas === 1 ? '' : 's'}
                </div>
              </button>
            ))}
          </div>

          <form onSubmit={crearNb} className="flex gap-2 max-w-md">
            <input
              value={nuevoNb}
              onChange={(e) => setNuevoNb(e.target.value)}
              placeholder="Nuevo cuaderno…"
              className={`${inputCls} flex-1`}
            />
            <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
              Crear
            </button>
          </form>
        </>
      )}
    </div>
  )
}

function SpecialCard({
  titulo,
  onClick,
}: {
  titulo: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="text-left rounded-xl border border-slate-800 bg-slate-800/40 p-4 hover:border-slate-600 transition"
    >
      <div className="text-2xl">🗂️</div>
      <div className="font-medium mt-2">{titulo}</div>
    </button>
  )
}

function Detalle({
  sel,
  notebooks,
  nombreCuaderno,
  onVolver,
}: {
  sel: Seleccion
  notebooks: Notebook[]
  nombreCuaderno: (id: string | null) => string | null
  onVolver: () => void
}) {
  const [notas, setNotas] = useState<Note[]>([])
  const [nueva, setNueva] = useState('')
  const [cargando, setCargando] = useState(true)

  const nbId = sel.tipo === 'cuaderno' ? sel.nb.id : undefined
  const titulo =
    sel.tipo === 'cuaderno'
      ? sel.nb.nombre
      : sel.tipo === 'sin'
        ? 'Sin cuaderno'
        : 'Todas las notas'

  const cargar = useCallback(() => {
    const opts =
      sel.tipo === 'cuaderno'
        ? { notebookId: sel.nb.id }
        : sel.tipo === 'sin'
          ? { sinCuaderno: true }
          : undefined
    api
      .listNotes(opts)
      .then(setNotas)
      .finally(() => setCargando(false))
  }, [sel])

  useEffect(() => {
    cargar()
  }, [cargar])

  const crear = async (e: FormEvent) => {
    e.preventDefault()
    if (!nueva.trim()) return
    // En un cuaderno se guarda ahí; en 'todas'/'sin' queda sin cuaderno.
    await api.createNote(nueva.trim(), nbId ?? null)
    setNueva('')
    cargar()
  }
  const eliminar = async (id: string) => {
    await api.deleteNote(id)
    cargar()
  }
  const mover = async (id: string, destino: string) => {
    await api.moveNote(id, destino || null)
    cargar()
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <button
          onClick={onVolver}
          className="text-slate-400 hover:text-slate-200 text-sm"
        >
          ← Cuadernos
        </button>
        <h2 className="text-xl font-semibold">📓 {titulo}</h2>
      </div>

      <form onSubmit={crear} className="flex gap-2">
        <input
          value={nueva}
          onChange={(e) => setNueva(e.target.value)}
          placeholder={
            sel.tipo === 'cuaderno'
              ? `Escribe una nota en ${sel.nb.nombre}…`
              : 'Escribe una nota…'
          }
          className={`${inputCls} flex-1`}
        />
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Guardar
        </button>
      </form>

      {cargando ? (
        <p className="text-slate-500">Cargando…</p>
      ) : notas.length === 0 ? (
        <p className="text-slate-500">Sin notas aquí.</p>
      ) : (
        <ul className="space-y-2">
          {notas.map((n) => (
            <li
              key={n.id}
              className="group rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-3 flex items-start justify-between gap-3"
            >
              <div className="min-w-0">
                <p className="whitespace-pre-wrap">{n.contenido}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {new Date(n.creada).toLocaleString('es-CO')}
                  {sel.tipo === 'todas' && nombreCuaderno(n.notebook_id) && (
                    <span className="ml-2">· 📓 {nombreCuaderno(n.notebook_id)}</span>
                  )}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <select
                  value={n.notebook_id ?? ''}
                  onChange={(e) => mover(n.id, e.target.value)}
                  className="opacity-0 group-hover:opacity-100 rounded bg-slate-900 border border-slate-700 text-xs px-1.5 py-1 transition"
                  title="Mover a cuaderno"
                >
                  <option value="">— sin cuaderno —</option>
                  {notebooks.map((nb) => (
                    <option key={nb.id} value={nb.id}>
                      {nb.nombre}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => eliminar(n.id)}
                  className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 text-sm transition"
                >
                  Eliminar
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
