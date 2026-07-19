import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'
import { useTheme } from '../theme'

const SECCIONES = [
  { to: '/notas', label: 'Notas', icon: '📝' },
  { to: '/proyectos', label: 'Proyectos', icon: '📋' },
  { to: '/tareas', label: 'Tareas', icon: '✅' },
  { to: '/finanzas', label: 'Finanzas', icon: '💰' },
  { to: '/mercado', label: 'Mercado', icon: '🛒' },
  { to: '/responsabilidades', label: 'Responsabilidades', icon: '🔁' },
  { to: '/recordatorios', label: 'Recordatorios', icon: '⏰' },
]

const navClase = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm transition ${
    isActive
      ? 'bg-[var(--c-brand-soft)] text-brand font-medium'
      : 'text-muted hover:bg-surface hover:text-ink'
  }`

export default function Layout() {
  const { usuario, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const [menu, setMenu] = useState(false)
  const cerrar = () => setMenu(false)

  return (
    <div className="min-h-screen bg-ground text-ink md:flex">
      {/* Barra superior (solo móvil) */}
      <header className="md:hidden sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-surface-2 px-4 py-3">
        <button
          onClick={() => setMenu(true)}
          aria-label="Abrir menú"
          className="p-1 text-ink"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M3 6h18M3 12h18M3 18h18" />
          </svg>
        </button>
        <img src="/logo-simbolo.png" alt="" className="size-7 rounded-md object-cover" />
        <span className="font-serif text-lg">Puiky</span>
      </header>

      {/* Backdrop del cajón (solo móvil) */}
      {menu && (
        <div
          onClick={cerrar}
          className="md:hidden fixed inset-0 z-40 bg-black/40"
          aria-hidden
        />
      )}

      {/* Barra lateral: cajón deslizante en móvil, fija en escritorio */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 border-r border-line bg-surface-2 flex flex-col transition-transform duration-200 md:static md:z-auto md:w-60 md:translate-x-0 ${
          menu ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center gap-3 px-5 py-5">
          <img
            src="/logo-simbolo.png"
            alt="Puiky"
            className="size-9 rounded-lg object-cover shrink-0"
          />
          <div className="flex-1">
            <div className="font-serif text-lg leading-none text-ink">Puiky</div>
            <div className="eyebrow mt-1">tu segundo cerebro</div>
          </div>
          <button
            onClick={cerrar}
            aria-label="Cerrar menú"
            className="md:hidden p-1 text-muted hover:text-ink"
          >
            ✕
          </button>
        </div>

        <nav className="flex-1 px-3 space-y-0.5 overflow-y-auto">
          {SECCIONES.map((s) => (
            <NavLink key={s.to} to={s.to} onClick={cerrar} className={navClase}>
              <span className="text-base">{s.icon}</span>
              {s.label}
            </NavLink>
          ))}

          <div className="pt-2 mt-2 border-t border-line">
            <NavLink to="/concepto" onClick={cerrar} className={navClase}>
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

      <main className="flex-1 min-w-0 px-4 py-6 md:px-8 md:py-8 overflow-x-auto">
        <Outlet />
      </main>
    </div>
  )
}
