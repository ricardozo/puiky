import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, type Project } from '../api'

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [nombre, setNombre] = useState('')
  const [cargando, setCargando] = useState(true)

  const cargar = () =>
    api.listProjects().then(setProjects).finally(() => setCargando(false))

  useEffect(() => {
    cargar()
  }, [])

  const crear = async (e: FormEvent) => {
    e.preventDefault()
    if (!nombre.trim()) return
    await api.createProject(nombre.trim())
    setNombre('')
    cargar()
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Proyectos</h2>

      <form onSubmit={crear} className="flex gap-2 max-w-xl">
        <input
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Nuevo proyecto…"
          className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 outline-none focus:border-indigo-500"
        />
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Crear
        </button>
      </form>

      {cargando ? (
        <p className="text-slate-500">Cargando…</p>
      ) : projects.length === 0 ? (
        <p className="text-slate-500">Sin proyectos todavía.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <Link
              key={p.id}
              to={`/proyectos/${p.id}`}
              className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 hover:border-slate-600 transition"
            >
              <div className="font-medium">{p.nombre}</div>
              {p.descripcion && (
                <div className="text-sm text-slate-400 mt-1">{p.descripcion}</div>
              )}
              <div className="mt-3 inline-block rounded px-2 py-0.5 text-xs bg-slate-800 text-slate-400">
                {p.estado}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
