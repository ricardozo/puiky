import { useState, type FormEvent } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useAuth } from '../auth'
import { useTheme } from '../theme'

function CambiarClave({ onCerrar }: { onCerrar: () => void }) {
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [error, setError] = useState('')
  const [listo, setListo] = useState(false)
  const [busy, setBusy] = useState(false)

  const guardar = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (nueva.length < 6) return setError('La clave nueva debe tener al menos 6 caracteres.')
    if (nueva !== confirmar) return setError('La confirmación no coincide.')
    setBusy(true)
    try {
      await api.changePassword(actual, nueva)
      setListo(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo cambiar la clave')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[60] bg-black/50 grid place-items-center p-4"
      onClick={onCerrar}
    >
      <div
        className="card w-full max-w-sm p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-serif text-xl">Cambiar clave</h3>
        {listo ? (
          <>
            <p className="text-sm text-[color:var(--c-green)]">
              ✅ Clave cambiada. Úsala en tu próximo ingreso.
            </p>
            <div className="flex justify-end">
              <button onClick={onCerrar} className="btn">
                Listo
              </button>
            </div>
          </>
        ) : (
          <form onSubmit={guardar} className="space-y-3">
            <label className="text-xs text-muted flex flex-col gap-1">
              Clave actual
              <input
                type="password"
                value={actual}
                onChange={(e) => setActual(e.target.value)}
                autoFocus
                className="input"
              />
            </label>
            <label className="text-xs text-muted flex flex-col gap-1">
              Clave nueva (mínimo 6)
              <input
                type="password"
                value={nueva}
                onChange={(e) => setNueva(e.target.value)}
                className="input"
              />
            </label>
            <label className="text-xs text-muted flex flex-col gap-1">
              Confirmar clave nueva
              <input
                type="password"
                value={confirmar}
                onChange={(e) => setConfirmar(e.target.value)}
                className="input"
              />
            </label>
            {error && (
              <p className="text-[color:var(--c-danger)] text-sm">{error}</p>
            )}
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={onCerrar} className="btn-ghost btn">
                Cancelar
              </button>
              <button disabled={busy} className="btn">
                {busy ? 'Guardando…' : 'Guardar'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

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
  const [clave, setClave] = useState(false)
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
          <button
            onClick={() => setClave(true)}
            title="Cambiar clave"
            className="text-muted flex-1 truncate px-1 text-left hover:text-ink transition"
          >
            {usuario} <span className="text-faint">· 🔑</span>
          </button>
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

      {clave && <CambiarClave onCerrar={() => setClave(false)} />}
    </div>
  )
}
