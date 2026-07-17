import { useAuth } from './auth'
import Login from './pages/Login'
import Notes from './pages/Notes'

export default function App() {
  const { usuario, loading, logout } = useAuth()

  if (loading)
    return (
      <div className="min-h-screen grid place-items-center bg-slate-950 text-slate-400">
        Cargando…
      </div>
    )

  if (!usuario) return <Login />

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <div className="flex items-baseline gap-2">
          <span className="text-xl font-semibold">Puiky</span>
          <span className="text-slate-500 text-sm">tu segundo cerebro</span>
        </div>
        <div className="flex items-center gap-3 text-sm text-slate-400">
          <span>{usuario}</span>
          <button
            onClick={logout}
            className="rounded-md border border-slate-700 px-3 py-1 hover:bg-slate-800 transition"
          >
            Salir
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-8">
        <Notes />
      </main>
    </div>
  )
}
