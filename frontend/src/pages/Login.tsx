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
    <div className="min-h-screen grid place-items-center bg-ground text-ink px-4">
      <form onSubmit={submit} className="w-full max-w-sm">
        <div className="text-center mb-8">
          <img
            src="/logo-simbolo.png"
            alt="Puiky"
            className="size-20 rounded-2xl object-cover mx-auto shadow-[var(--shadow)]"
          />
          <h1 className="font-serif text-4xl mt-5 tracking-tight">Puiky</h1>
          <p className="eyebrow mt-2">tu segundo cerebro</p>
        </div>
        <div className="space-y-3">
          <input
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
            placeholder="Usuario"
            autoFocus
            className="input"
          />
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="Contraseña"
            className="input"
          />
        </div>
        {error && <p className="text-[color:var(--c-danger)] text-sm mt-3">{error}</p>}
        <button disabled={busy} className="btn w-full mt-5 py-2.5">
          {busy ? 'Entrando…' : 'Iniciar sesión'}
        </button>
      </form>
    </div>
  )
}
