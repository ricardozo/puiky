import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Notes from './pages/Notes'
import Projects from './pages/Projects'
import Board from './pages/Board'
import Finanzas from './pages/Finanzas'
import Recordatorios from './pages/Recordatorios'
import Responsabilidades from './pages/Responsabilidades'
import Tareas from './pages/Tareas'

export default function App() {
  const { usuario, loading } = useAuth()

  if (loading)
    return (
      <div className="min-h-screen grid place-items-center bg-slate-950 text-slate-400">
        Cargando…
      </div>
    )

  if (!usuario) return <Login />

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/notas" replace />} />
        <Route path="notas" element={<Notes />} />
        <Route path="proyectos" element={<Projects />} />
        <Route path="proyectos/:id" element={<Board />} />
        <Route path="tareas" element={<Tareas />} />
        <Route path="finanzas" element={<Finanzas />} />
        <Route path="responsabilidades" element={<Responsabilidades />} />
        <Route path="recordatorios" element={<Recordatorios />} />
        <Route path="*" element={<Navigate to="/notas" replace />} />
      </Route>
    </Routes>
  )
}
