import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, getToken, setToken } from './api'

interface AuthCtx {
  usuario: string | null
  loading: boolean
  login: (usuario: string, password: string) => Promise<void>
  logout: () => void
}

const Ctx = createContext<AuthCtx>(null!)
// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!getToken()) {
      setLoading(false)
      return
    }
    api
      .me()
      .then((r) => setUsuario(r.usuario))
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (u: string, p: string) => {
    const r = await api.login(u, p)
    setToken(r.access_token)
    const me = await api.me()
    setUsuario(me.usuario)
  }
  const logout = () => {
    setToken(null)
    setUsuario(null)
  }

  return <Ctx.Provider value={{ usuario, loading, login, logout }}>{children}</Ctx.Provider>
}
