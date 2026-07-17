import { useEffect, useState, type FormEvent } from 'react'
import { api, type Note, type SearchResult } from '../api'

export default function Notes() {
  const [notes, setNotes] = useState<Note[]>([])
  const [nueva, setNueva] = useState('')
  const [query, setQuery] = useState('')
  const [resultados, setResultados] = useState<SearchResult[] | null>(null)
  const [cargando, setCargando] = useState(true)

  const cargar = () =>
    api.listNotes().then(setNotes).finally(() => setCargando(false))

  useEffect(() => {
    cargar()
  }, [])

  const crear = async (e: FormEvent) => {
    e.preventDefault()
    if (!nueva.trim()) return
    await api.createNote(nueva.trim())
    setNueva('')
    setResultados(null)
    cargar()
  }

  const buscar = async (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) {
      setResultados(null)
      return
    }
    setResultados(await api.searchNotes(query.trim()))
  }

  const eliminar = async (id: string) => {
    await api.deleteNote(id)
    setResultados(null)
    cargar()
  }

  const lista: Note[] = resultados ?? notes

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Notas</h2>

      <form onSubmit={crear} className="flex gap-2">
        <input
          value={nueva}
          onChange={(e) => setNueva(e.target.value)}
          placeholder="Escribe una nota…"
          className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 outline-none focus:border-indigo-500"
        />
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Guardar
        </button>
      </form>

      <form onSubmit={buscar} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Búsqueda semántica (por significado)…"
          className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 outline-none focus:border-indigo-500"
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

      {resultados && (
        <p className="text-sm text-slate-400">
          {resultados.length} resultado(s) por significado
        </p>
      )}

      {cargando ? (
        <p className="text-slate-500">Cargando…</p>
      ) : (
        <ul className="space-y-2">
          {lista.length === 0 && (
            <li className="text-slate-500">Sin notas todavía.</li>
          )}
          {lista.map((n) => (
            <li
              key={n.id}
              className="group rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-3 flex items-start justify-between gap-3"
            >
              <div>
                <p className="whitespace-pre-wrap">{n.contenido}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {new Date(n.creada).toLocaleString('es-CO')}
                  {'similitud' in n && (
                    <span className="ml-2 text-indigo-400">
                      · {((n as SearchResult).similitud * 100).toFixed(0)}% afín
                    </span>
                  )}
                </p>
              </div>
              <button
                onClick={() => eliminar(n.id)}
                className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 text-sm transition"
              >
                Eliminar
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
