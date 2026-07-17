import { useState, type FormEvent } from 'react'
import { useAuth } from '../auth'

export default function Login() {
  const { login } = useAuth()
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(usuario, password)
    } catch {
      setError('Usuario o contraseña incorrectos')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-slate-950 text-slate-100 px-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-4xl font-semibold tracking-tight">Puiky</h1>
          <p className="text-slate-400 text-sm mt-2">
            El corazón y la mente, donde se piensa y se recuerda.
          </p>
        </div>
        <div className="space-y-3">
          <input
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
            placeholder="Usuario"
            autoFocus
            className="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 outline-none focus:border-indigo-500"
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="Contraseña"
            className="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 outline-none focus:border-indigo-500"
          />
        </div>
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button
          disabled={busy}
          className="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 py-2.5 font-medium transition"
        >
          {busy ? 'Entrando…' : 'Iniciar sesión'}
        </button>
      </form>
    </div>
  )
}
