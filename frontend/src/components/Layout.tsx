import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'

const SECCIONES = [
  { to: '/notas', label: 'Notas', icon: '📝' },
  { to: '/proyectos', label: 'Proyectos', icon: '📋' },
  { to: '/tareas', label: 'Tareas', icon: '✅' },
  { to: '/finanzas', label: 'Finanzas', icon: '💰' },
  { to: '/responsabilidades', label: 'Responsabilidades', icon: '🔁' },
  { to: '/recordatorios', label: 'Recordatorios', icon: '⏰' },
]

export default function Layout() {
  const { usuario, logout } = useAuth()

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <aside className="w-56 shrink-0 border-r border-slate-800 flex flex-col">
        <div className="px-5 py-5">
          <div className="text-xl font-semibold">Puiky</div>
          <div className="text-xs text-slate-500">tu segundo cerebro</div>
        </div>
        <nav className="flex-1 px-3 space-y-1">
          {SECCIONES.map((s) => (
            <NavLink
              key={s.to}
              to={s.to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-indigo-600/20 text-indigo-300'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`
              }
            >
              <span>{s.icon}</span>
              {s.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-3 py-4 border-t border-slate-800 flex items-center justify-between text-sm">
          <span className="text-slate-400 px-2">{usuario}</span>
          <button
            onClick={logout}
            className="rounded-md border border-slate-700 px-3 py-1 text-slate-300 hover:bg-slate-800 transition"
          >
            Salir
          </button>
        </div>
      </aside>

      <main className="flex-1 px-8 py-8 overflow-x-auto">
        <Outlet />
      </main>
    </div>
  )
}
