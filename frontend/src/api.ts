// Cliente HTTP de la API de Puiky. Adjunta el JWT de sesión guardado.

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'puiky_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t)
  else localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string>),
  }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...opts, headers })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(res.status, (data && data.detail) || res.statusText)
  }
  return data as T
}

export interface Note {
  id: string
  contenido: string
  creada: string
}
export interface SearchResult extends Note {
  similitud: number
}

export interface Project {
  id: string
  nombre: string
  descripcion: string | null
  estado: string
}
export interface Task {
  id: string
  project_id: string | null
  titulo: string
  estado: string
  avance_pct: number
  fecha_limite: string | null
}
export interface ProjectDetail extends Project {
  tasks: Task[]
  notes: Note[]
}

export const api = {
  login: (usuario: string, password: string) =>
    request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ usuario, password }),
    }),
  me: () => request<{ usuario: string }>('/auth/me'),
  listNotes: () => request<Note[]>('/notes'),
  createNote: (contenido: string) =>
    request<Note>('/notes', {
      method: 'POST',
      body: JSON.stringify({ contenido }),
    }),
  searchNotes: (texto: string) =>
    request<SearchResult[]>('/notes/search', {
      method: 'POST',
      body: JSON.stringify({ texto, limite: 10 }),
    }),
  deleteNote: (id: string) =>
    request<void>(`/notes/${id}`, { method: 'DELETE' }),

  // Proyectos
  listProjects: () => request<Project[]>('/projects'),
  getProject: (id: string) => request<ProjectDetail>(`/projects/${id}`),
  createProject: (nombre: string, descripcion?: string) =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ nombre, descripcion: descripcion || null }),
    }),

  // Tareas
  createTask: (titulo: string, projectId: string) =>
    request<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify({ titulo, project_id: projectId }),
    }),
  updateTaskEstado: (id: string, estado: string) =>
    request<Task>(`/tasks/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ estado }),
    }),
  deleteTask: (id: string) =>
    request<void>(`/tasks/${id}`, { method: 'DELETE' }),
}
