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
    let msg = res.statusText
    const detail = data?.detail
    if (typeof detail === 'string') msg = detail
    else if (Array.isArray(detail))
      msg = detail
        .map((e: { msg?: string }) => e.msg)
        .filter(Boolean)
        .join('; ')
    throw new ApiError(res.status, msg)
  }
  return data as T
}

export interface Note {
  id: string
  titulo: string | null
  contenido: string
  notebook_id: string | null
  creada: string
  actualizada: string
}
export interface SearchResult extends Note {
  similitud: number
}
export interface Notebook {
  id: string
  nombre: string
  descripcion: string | null
  creada: string
  notas: number
}

export interface Project {
  id: string
  nombre: string
  descripcion: string | null
  estado: string
  portfolio_id: string | null
}
export interface Portfolio {
  id: string
  nombre: string
  descripcion: string | null
  creada: string
  proyectos: number
}
export interface ChecklistItem {
  id: string
  texto: string
  hecho: boolean
  orden: number
}
export interface Task {
  id: string
  project_id: string | null
  proyecto: string | null
  titulo: string
  descripcion: string | null
  notas: string | null
  estado: string
  avance_pct: number
  fecha_limite: string | null
  fecha_inicio_plan: string | null
  fecha_inicio_real: string | null
  fecha_fin_real: string | null
  checklist: ChecklistItem[]
}
export interface TaskFechas {
  titulo?: string
  descripcion?: string | null
  notas?: string | null
  fecha_limite?: string | null
  fecha_inicio_plan?: string | null
  fecha_inicio_real?: string | null
  fecha_fin_real?: string | null
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

export interface Reminder {
  id: string
  origen_tipo: string | null
  origen_id: string | null
  texto: string
  disparar_en: string
  veces_avisado: number
  pospuesto_para: string | null
  resuelto: boolean
}
export interface Responsibility {
  id: string
  nombre: string
  recurrencia: string
  proximo_venc: string
  monto: string | null
}

export const api = {
  login: (usuario: string, password: string) =>
    request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ usuario, password }),
    }),
  me: () => request<{ usuario: string }>('/auth/me'),
  listNotes: (opts?: { notebookId?: string; sinCuaderno?: boolean }) => {
    let q = ''
    if (opts?.sinCuaderno) q = '?sin_cuaderno=true'
    else if (opts?.notebookId) q = `?notebook_id=${opts.notebookId}`
    return request<Note[]>(`/notes${q}`)
  },
  createNote: (
    contenido: string,
    notebookId?: string | null,
    titulo?: string | null
  ) =>
    request<Note>('/notes', {
      method: 'POST',
      body: JSON.stringify({
        contenido,
        notebook_id: notebookId ?? null,
        titulo: titulo ?? null,
      }),
    }),
  updateNote: (
    id: string,
    data: { titulo?: string | null; contenido?: string; notebook_id?: string | null }
  ) => request<Note>(`/notes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  appendNote: (id: string, texto: string) =>
    request<Note>(`/notes/${id}/append`, {
      method: 'POST',
      body: JSON.stringify({ texto }),
    }),
  moveNote: (id: string, notebookId: string | null) =>
    request<Note>(`/notes/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ notebook_id: notebookId }),
    }),
  searchNotes: (texto: string) =>
    request<SearchResult[]>('/notes/search', {
      method: 'POST',
      body: JSON.stringify({ texto, limite: 10 }),
    }),
  deleteNote: (id: string) =>
    request<void>(`/notes/${id}`, { method: 'DELETE' }),

  // Cuadernos
  listNotebooks: () => request<Notebook[]>('/notebooks'),
  createNotebook: (nombre: string, descripcion?: string) =>
    request<Notebook>('/notebooks', {
      method: 'POST',
      body: JSON.stringify({ nombre, descripcion: descripcion || null }),
    }),
  deleteNotebook: (id: string) =>
    request<void>(`/notebooks/${id}`, { method: 'DELETE' }),

  // Proyectos
  listProjects: (opts?: { portfolioId?: string; sinPortafolio?: boolean }) => {
    let q = ''
    if (opts?.sinPortafolio) q = '?sin_portafolio=true'
    else if (opts?.portfolioId) q = `?portfolio_id=${opts.portfolioId}`
    return request<Project[]>(`/projects${q}`)
  },
  getProject: (id: string) => request<ProjectDetail>(`/projects/${id}`),
  listTasks: (q?: string) =>
    request<Task[]>(`/tasks${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  createProject: (nombre: string, portfolioId?: string | null) =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ nombre, portfolio_id: portfolioId ?? null }),
    }),
  moveProject: (id: string, portfolioId: string | null) =>
    request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ portfolio_id: portfolioId }),
    }),

  // Portafolios
  listPortfolios: () => request<Portfolio[]>('/portfolios'),
  createPortfolio: (nombre: string, descripcion?: string) =>
    request<Portfolio>('/portfolios', {
      method: 'POST',
      body: JSON.stringify({ nombre, descripcion: descripcion || null }),
    }),
  deletePortfolio: (id: string) =>
    request<void>(`/portfolios/${id}`, { method: 'DELETE' }),

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
  updateTask: (id: string, data: TaskFechas & { estado?: string }) =>
    request<Task>(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  completeTask: (id: string) =>
    request<Task>(`/tasks/${id}/complete`, { method: 'POST' }),
  deleteTask: (id: string) =>
    request<void>(`/tasks/${id}`, { method: 'DELETE' }),
  addChecklistItem: (taskId: string, texto: string) =>
    request<Task>(`/tasks/${taskId}/checklist`, {
      method: 'POST',
      body: JSON.stringify({ texto }),
    }),
  toggleChecklistItem: (itemId: string, hecho: boolean) =>
    request<Task>(`/tasks/checklist/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify({ hecho }),
    }),
  deleteChecklistItem: (itemId: string) =>
    request<Task>(`/tasks/checklist/${itemId}`, { method: 'DELETE' }),

  // Hojas vinculadas a una entidad (p. ej. una tarea)
  linkedNotes: (entidadTipo: string, entidadId: string) =>
    request<Note[]>(
      `/notes/vinculadas?entidad_tipo=${entidadTipo}&entidad_id=${entidadId}`
    ),
  linkNote: (noteId: string, entidadTipo: string, entidadId: string) =>
    request<unknown>(`/notes/${noteId}/links`, {
      method: 'POST',
      body: JSON.stringify({ entidad_tipo: entidadTipo, entidad_id: entidadId }),
    }),
  unlinkNote: (noteId: string, entidadTipo: string, entidadId: string) =>
    request<void>(
      `/notes/${noteId}/links?entidad_tipo=${entidadTipo}&entidad_id=${entidadId}`,
      { method: 'DELETE' }
    ),

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

  // Recordatorios
  listReminders: (resuelto?: boolean) =>
    request<Reminder[]>(
      `/reminders${resuelto === undefined ? '' : `?resuelto=${resuelto}`}`
    ),
  createReminder: (texto: string, dispararEn: string) =>
    request<Reminder>('/reminders', {
      method: 'POST',
      body: JSON.stringify({ texto, disparar_en: dispararEn }),
    }),
  snoozeReminder: (id: string, pospuestoPara: string) =>
    request<Reminder>(`/reminders/${id}/snooze`, {
      method: 'POST',
      body: JSON.stringify({ pospuesto_para: pospuestoPara }),
    }),
  resolveReminder: (id: string) =>
    request<Reminder>(`/reminders/${id}/resolve`, { method: 'POST' }),
  deleteReminder: (id: string) =>
    request<void>(`/reminders/${id}`, { method: 'DELETE' }),

  // Responsabilidades
  listResponsibilities: () => request<Responsibility[]>('/responsibilities'),
  createResponsibility: (
    nombre: string,
    recurrencia: string,
    proximoVenc: string,
    monto: number | null
  ) =>
    request<Responsibility>('/responsibilities', {
      method: 'POST',
      body: JSON.stringify({
        nombre,
        recurrencia,
        proximo_venc: proximoVenc,
        monto,
      }),
    }),
  fulfillResponsibility: (id: string) =>
    request<Responsibility>(`/responsibilities/${id}/fulfill`, {
      method: 'POST',
    }),
  deleteResponsibility: (id: string) =>
    request<void>(`/responsibilities/${id}`, { method: 'DELETE' }),
}

export function fmtMoney(v: string | number): string {
  return Number(v).toLocaleString('es-CO', { maximumFractionDigits: 0 })
}

// datetime-local ("YYYY-MM-DDTHH:MM") -> ISO con offset de Colombia (-05:00).
export function aISOColombia(local: string): string {
  return `${local}:00-05:00`
}

