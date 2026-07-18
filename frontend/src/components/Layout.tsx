import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'
import { useTheme } from '../theme'

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
  const { theme, toggle } = useTheme()

  return (
    <div className="min-h-screen bg-ground text-ink flex">
      <aside className="w-60 shrink-0 border-r border-line bg-surface-2 flex flex-col">
        <div className="flex items-center gap-3 px-5 py-5">
          <img
            src="/logo-simbolo.png"
            alt="Puiky"
            className="size-9 rounded-lg object-cover shrink-0"
          />
          <div>
            <div className="font-serif text-lg leading-none text-ink">Puiky</div>
            <div className="eyebrow mt-1">tu segundo cerebro</div>
          </div>
        </div>

        <nav className="flex-1 px-3 space-y-0.5">
          {SECCIONES.map((s) => (
            <NavLink
              key={s.to}
              to={s.to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-[var(--c-brand-soft)] text-brand font-medium'
                    : 'text-muted hover:bg-surface hover:text-ink'
                }`
              }
            >
              <span className="text-base">{s.icon}</span>
              {s.label}
            </NavLink>
          ))}

          <div className="pt-2 mt-2 border-t border-line">
            <NavLink
              to="/concepto"
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-[var(--c-brand-soft)] text-brand font-medium'
                    : 'text-muted hover:bg-surface hover:text-ink'
                }`
              }
            >
              <span className="text-base">✦</span>
              ¿Qué es Puiky?
            </NavLink>
          </div>
        </nav>

        <div className="px-4 py-4 border-t border-line flex items-center gap-2 text-sm">
          <span className="text-muted flex-1 truncate px-1">{usuario}</span>
          <button
            onClick={toggle}
            title="Cambiar tema"
            className="rounded-lg border border-line px-2.5 py-1.5 text-muted hover:text-ink hover:bg-surface transition"
          >
            {theme === 'dark' ? '☀' : '☾'}
          </button>
          <button
            onClick={logout}
            className="rounded-lg border border-line px-3 py-1.5 text-muted hover:text-ink hover:bg-surface transition"
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
