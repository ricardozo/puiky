import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type Note, type Notebook, type SearchResult } from '../api'

const inputCls =
  'rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 outline-none focus:border-indigo-500'

type Seleccion =
  | { tipo: 'home' }
  | { tipo: 'todas' }
  | { tipo: 'sin' }
  | { tipo: 'cuaderno'; nb: Notebook }

type Editor =
  | { modo: 'nueva'; notebookId: string | null }
  | { modo: 'editar'; nota: Note }

function tituloTarjeta(n: Note): string {
  return n.titulo || n.contenido.split('\n')[0].slice(0, 80) || '(sin título)'
}
function cuerpoTarjeta(n: Note): string {
  const cuerpo = n.titulo ? n.contenido : n.contenido.split('\n').slice(1).join(' ')
  return cuerpo.slice(0, 160)
}

export default function Notes() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([])
  const [sel, setSel] = useState<Seleccion>({ tipo: 'home' })
  const [editor, setEditor] = useState<Editor | null>(null)

  const cargarNotebooks = useCallback(
    () => api.listNotebooks().then(setNotebooks),
    []
  )
  useEffect(() => {
    cargarNotebooks()
  }, [cargarNotebooks])

  const nombreCuaderno = (id: string | null) =>
    id ? notebooks.find((n) => n.id === id)?.nombre ?? '—' : null

  const cerrarEditor = () => {
    cargarNotebooks()
    setEditor(null)
  }

  if (editor)
    return (
      <HojaEditor
        editor={editor}
        notebooks={notebooks}
        onGuardado={cerrarEditor}
        onVolver={() => setEditor(null)}
      />
    )

  if (sel.tipo === 'home')
    return (
      <Home
        notebooks={notebooks}
        nombreCuaderno={nombreCuaderno}
        onAbrir={setSel}
        onAbrirNota={(n) => setEditor({ modo: 'editar', nota: n })}
        onCambio={cargarNotebooks}
      />
    )

  return (
    <Detalle
      sel={sel}
      nombreCuaderno={nombreCuaderno}
      onVolver={() => {
        cargarNotebooks()
        setSel({ tipo: 'home' })
      }}
      onNueva={(nbId) => setEditor({ modo: 'nueva', notebookId: nbId })}
      onAbrirNota={(n) => setEditor({ modo: 'editar', nota: n })}
    />
  )
}

function Home({
  notebooks,
  nombreCuaderno,
  onAbrir,
  onAbrirNota,
  onCambio,
}: {
  notebooks: Notebook[]
  nombreCuaderno: (id: string | null) => string | null
  onAbrir: (s: Seleccion) => void
  onAbrirNota: (n: Note) => void
  onCambio: () => void
}) {
  const [query, setQuery] = useState('')
  const [resultados, setResultados] = useState<SearchResult[] | null>(null)
  const [nuevoNb, setNuevoNb] = useState('')

  const buscar = async (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return setResultados(null)
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
            <button
              key={n.id}
              onClick={() => onAbrirNota(n)}
              className="block w-full text-left rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-3 hover:border-slate-600 transition"
            >
              <div className="font-medium">{tituloTarjeta(n)}</div>
              <div className="text-sm text-slate-400 mt-0.5 line-clamp-2">
                {cuerpoTarjeta(n)}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                <span className="text-indigo-400">
                  {(n.similitud * 100).toFixed(0)}% afín
                </span>
                {nombreCuaderno(n.notebook_id) && (
                  <span className="ml-2">📓 {nombreCuaderno(n.notebook_id)}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <SpecialCard titulo="Todas las notas" onClick={() => onAbrir({ tipo: 'todas' })} />
            <SpecialCard titulo="Sin cuaderno" onClick={() => onAbrir({ tipo: 'sin' })} />
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

function SpecialCard({ titulo, onClick }: { titulo: string; onClick: () => void }) {
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
  nombreCuaderno,
  onVolver,
  onNueva,
  onAbrirNota,
}: {
  sel: Seleccion
  nombreCuaderno: (id: string | null) => string | null
  onVolver: () => void
  onNueva: (notebookId: string | null) => void
  onAbrirNota: (n: Note) => void
}) {
  const [notas, setNotas] = useState<Note[]>([])
  const [cargando, setCargando] = useState(true)

  const nbId = sel.tipo === 'cuaderno' ? sel.nb.id : null
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
    api.listNotes(opts).then(setNotas).finally(() => setCargando(false))
  }, [sel])

  useEffect(() => {
    cargar()
  }, [cargar])

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={onVolver} className="text-slate-400 hover:text-slate-200 text-sm">
            ← Cuadernos
          </button>
          <h2 className="text-xl font-semibold">📓 {titulo}</h2>
        </div>
        <button
          onClick={() => onNueva(nbId)}
          className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 py-2 font-medium text-sm"
        >
          + Nueva hoja
        </button>
      </div>

      {cargando ? (
        <p className="text-slate-500">Cargando…</p>
      ) : notas.length === 0 ? (
        <p className="text-slate-500">Sin hojas aquí. Crea la primera.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {notas.map((n) => (
            <button
              key={n.id}
              onClick={() => onAbrirNota(n)}
              className="text-left rounded-xl border border-slate-800 bg-slate-900/50 p-4 hover:border-slate-600 transition"
            >
              <div className="font-medium">{tituloTarjeta(n)}</div>
              <div className="text-sm text-slate-400 mt-1 line-clamp-3 whitespace-pre-wrap">
                {cuerpoTarjeta(n)}
              </div>
              <div className="text-xs text-slate-500 mt-2">
                {new Date(n.actualizada).toLocaleDateString('es-CO')}
                {sel.tipo === 'todas' && nombreCuaderno(n.notebook_id) && (
                  <span className="ml-2">· 📓 {nombreCuaderno(n.notebook_id)}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function HojaEditor({
  editor,
  notebooks,
  onGuardado,
  onVolver,
}: {
  editor: Editor
  notebooks: Notebook[]
  onGuardado: () => void
  onVolver: () => void
}) {
  const nota = editor.modo === 'editar' ? editor.nota : null
  const [titulo, setTitulo] = useState(nota?.titulo ?? '')
  const [cuerpo, setCuerpo] = useState(nota?.contenido ?? '')
  const [notebookId, setNotebookId] = useState<string>(
    nota?.notebook_id ?? (editor.modo === 'nueva' ? editor.notebookId ?? '' : '')
  )
  const [guardando, setGuardando] = useState(false)

  const guardar = async () => {
    if (!cuerpo.trim()) return
    setGuardando(true)
    try {
      if (nota) {
        await api.updateNote(nota.id, {
          titulo: titulo.trim() || null,
          contenido: cuerpo.trim(),
          notebook_id: notebookId || null,
        })
      } else {
        await api.createNote(cuerpo.trim(), notebookId || null, titulo.trim() || null)
      }
      onGuardado()
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async () => {
    if (!nota) return
    await api.deleteNote(nota.id)
    onGuardado()
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <button onClick={onVolver} className="text-slate-400 hover:text-slate-200 text-sm">
        ← Volver
      </button>

      <input
        value={titulo}
        onChange={(e) => setTitulo(e.target.value)}
        placeholder="Título (opcional)"
        className="w-full bg-transparent text-2xl font-semibold outline-none placeholder:text-slate-600"
      />

      <textarea
        value={cuerpo}
        onChange={(e) => setCuerpo(e.target.value)}
        rows={16}
        placeholder="Escribe aquí…"
        className="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-3 outline-none focus:border-indigo-500 whitespace-pre-wrap"
      />

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={guardar}
          disabled={guardando}
          className="rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 px-5 py-2 font-medium"
        >
          {guardando ? 'Guardando…' : 'Guardar'}
        </button>
        <label className="text-sm text-slate-400 flex items-center gap-2">
          Cuaderno:
          <select
            value={notebookId}
            onChange={(e) => setNotebookId(e.target.value)}
            className="rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 outline-none focus:border-indigo-500"
          >
            <option value="">— sin cuaderno —</option>
            {notebooks.map((nb) => (
              <option key={nb.id} value={nb.id}>
                {nb.nombre}
              </option>
            ))}
          </select>
        </label>
        {nota && (
          <>
            <span className="text-xs text-slate-500">
              actualizada {new Date(nota.actualizada).toLocaleString('es-CO')}
            </span>
            <button
              onClick={eliminar}
              className="ml-auto text-slate-500 hover:text-red-400 text-sm"
            >
              Eliminar
            </button>
          </>
        )}
      </div>
    </div>
  )
}
