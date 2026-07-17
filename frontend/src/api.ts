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

// Los montos llegan como string (Decimal) desde la API.
export interface Account {
  id: string
  nombre: string
  tipo: string
  saldo: string
}
export interface Category {
  id: string
  nombre: string
  activa: boolean
}
export interface Transaction {
  id: string
  tipo: string
  monto: string
  account_id: string
  cuenta_destino_id: string | null
  category_id: string | null
  fecha: string
  nota: string | null
}
export interface Budget {
  id: string
  category_id: string | null
  tope: string
  periodo: string
}
export interface BudgetProgress extends Budget {
  gastado: string
  restante: string
  porcentaje: number
}
export interface NuevaTransaccion {
  tipo: string
  monto: number
  account_id: string
  cuenta_destino_id?: string | null
  category_id?: string | null
  nota?: string | null
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

  // Finanzas
  listAccounts: () => request<Account[]>('/accounts'),
  createAccount: (nombre: string, tipo: string, saldoInicial: number) =>
    request<Account>('/accounts', {
      method: 'POST',
      body: JSON.stringify({ nombre, tipo, saldo_inicial: saldoInicial }),
    }),
  listCategories: (soloActivas = true) =>
    request<Category[]>(`/categories?solo_activas=${soloActivas}`),
  listTransactions: () => request<Transaction[]>('/transactions'),
  createTransaction: (t: NuevaTransaccion) =>
    request<Transaction>('/transactions', {
      method: 'POST',
      body: JSON.stringify(t),
    }),
  deleteTransaction: (id: string) =>
    request<void>(`/transactions/${id}`, { method: 'DELETE' }),
  listBudgets: () => request<Budget[]>('/budgets'),
  budgetProgress: (id: string) =>
    request<BudgetProgress>(`/budgets/${id}/progreso`),
  createBudget: (tope: number, categoryId: string | null) =>
    request<Budget>('/budgets', {
      method: 'POST',
      body: JSON.stringify({ tope, category_id: categoryId }),
    }),
  deleteBudget: (id: string) =>
    request<void>(`/budgets/${id}`, { method: 'DELETE' }),
}

export function fmtMoney(v: string | number): string {
  return Number(v).toLocaleString('es-CO', { maximumFractionDigits: 0 })
}
