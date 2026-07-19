import { useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Landing from './pages/Landing'
import Notes from './pages/Notes'
import Projects from './pages/Projects'
import Board from './pages/Board'
import Finanzas from './pages/Finanzas'
import Recordatorios from './pages/Recordatorios'
import Responsabilidades from './pages/Responsabilidades'
import Tareas from './pages/Tareas'
import Concepto from './pages/Concepto'
import Mercado from './pages/Mercado'

export default function App() {
  const { usuario, loading } = useAuth()

  if (loading)
    return (
      <div className="min-h-screen grid place-items-center bg-ground text-muted">
        Cargando…
      </div>
    )

  if (!usuario) return <Publico />

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/notas" replace />} />
        <Route path="notas" element={<Notes />} />
        <Route path="proyectos" element={<Projects />} />
        <Route path="proyectos/:id" element={<Board />} />
        <Route path="tareas" element={<Tareas />} />
        <Route path="finanzas" element={<Finanzas />} />
        <Route path="mercado" element={<Mercado />} />
        <Route path="responsabilidades" element={<Responsabilidades />} />
        <Route path="recordatorios" element={<Recordatorios />} />
        <Route path="concepto" element={<Concepto />} />
        <Route path="*" element={<Navigate to="/notas" replace />} />
      </Route>
    </Routes>
  )
}

// Área pública (sin sesión): portada "¿Qué es Puiky?" con acceso al login.
function Publico() {
  const [verLogin, setVerLogin] = useState(false)
  return verLogin ? (
    <Login onVolver={() => setVerLogin(false)} />
  ) : (
    <Landing onEntrar={() => setVerLogin(true)} />
  )
}
