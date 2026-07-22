import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  DndContext,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { api, type Note, type ProjectDetail, type Task } from '../api'

const COLUMNAS = [
  { estado: 'planeada', titulo: 'Planeada' },
  { estado: 'en_ejecucion', titulo: 'En ejecución' },
  { estado: 'en_pausa', titulo: 'En pausa' },
  { estado: 'terminada', titulo: 'Terminada' },
]

function hechos(t: Task): number {
  return t.checklist.filter((i) => i.hecho).length
}

function Card({ task, onAbrir }: { task: Task; onAbrir: (t: Task) => void }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({ id: task.id })
  const style = transform
    ? { transform: `translate(${transform.x}px, ${transform.y}px)` }
    : undefined
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      onClick={() => onAbrir(task)}
      className={`rounded-lg border border-line bg-surface p-3 cursor-pointer active:cursor-grabbing shadow-[var(--shadow)] ${
        isDragging ? 'opacity-50' : ''
      }`}
    >
      <div className="text-sm">
        {task.recurrencia && <span title={`Recurrente: ${task.recurrencia}`}>🔁 </span>}
        {task.titulo}
      </div>
      {task.checklist.length > 0 && (
        <div className="text-xs text-muted mt-1.5">
          ☑ {hechos(task)}/{task.checklist.length}
        </div>
      )}
      {task.avance_pct > 0 && (
        <div className="mt-1.5 h-1 rounded-full bg-surface-2 overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{ width: `${task.avance_pct}%`, background: 'var(--c-teal)' }}
          />
        </div>
      )}
      {task.fecha_limite && (
        <div className="text-xs text-faint mt-1.5">vence {task.fecha_limite}</div>
      )}
    </div>
  )
}

function Column({
  estado,
  titulo,
  tasks,
  onAbrir,
}: {
  estado: string
  titulo: string
  tasks: Task[]
  onAbrir: (t: Task) => void
}) {
  const { setNodeRef, isOver } = useDroppable({ id: estado })
  return (
    <div
      ref={setNodeRef}
      className={`w-64 shrink-0 rounded-xl border p-3 transition ${
        isOver
          ? 'border-teal bg-[var(--c-brand-soft)]'
          : 'border-line bg-surface-2'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium">{titulo}</span>
        <span className="text-xs text-faint">{tasks.length}</span>
      </div>
      <div className="space-y-2 min-h-16">
        {tasks.map((t) => (
          <Card key={t.id} task={t} onAbrir={onAbrir} />
        ))}
      </div>
    </div>
  )
}

const hoyISO = () => {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

const RECURRENCIAS = [
  { v: '', label: 'No se repite' },
  { v: 'diaria', label: 'Diaria' },
  { v: 'semanal', label: 'Semanal' },
  { v: 'mensual', label: 'Mensual' },
  { v: 'trimestral', label: 'Trimestral' },
  { v: 'anual', label: 'Anual' },
]

function ProjectHeader({
  project,
  onCambio,
}: {
  project: ProjectDetail
  onCambio: () => void
}) {
  const [nombre, setNombre] = useState(project.nombre)
  const [desc, setDesc] = useState(project.descripcion ?? '')
  const guardar = (patch: Parameters<typeof api.updateProject>[1]) =>
    api.updateProject(project.id, patch).then(onCambio)
  const vencido =
    !!project.fecha_fin &&
    project.fecha_fin < hoyISO() &&
    project.estado !== 'terminado'

  return (
    <div className="card p-4 space-y-3 max-w-2xl">
      <input
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
        onBlur={() => {
          const v = nombre.trim()
          if (v && v !== project.nombre) guardar({ nombre: v })
        }}
        placeholder="Nombre del proyecto"
        className="input w-full font-serif text-lg"
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-baseline gap-2 text-sm">
          <span className="text-muted">
            {project.tareas_terminadas}/{project.total_tareas} tareas
          </span>
          <span className="font-medium">
            {project.avance === null ? 'sin tareas' : `${project.avance}% avance`}
          </span>
        </div>
        <select
          value={project.estado}
          onChange={(e) => guardar({ estado: e.target.value })}
          className="input w-auto py-1 text-sm"
        >
          <option value="activo">activo</option>
          <option value="pausado">pausado</option>
          <option value="terminado">terminado</option>
        </select>
      </div>
      {project.total_tareas > 0 && (
        <div className="h-2 rounded-full bg-[color:var(--c-surface-2)] overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{ width: `${project.avance}%`, background: 'var(--c-teal)' }}
          />
        </div>
      )}
      <textarea
        value={desc}
        onChange={(e) => setDesc(e.target.value)}
        onBlur={() => guardar({ descripcion: desc.trim() || null })}
        placeholder="Descripción del proyecto…"
        rows={2}
        className="input w-full text-sm"
      />
      <div className="grid grid-cols-2 gap-3">
        <Fecha
          label="Inicio"
          value={project.fecha_inicio}
          onChange={(v) => guardar({ fecha_inicio: v })}
        />
        <Fecha
          label="Fin"
          value={project.fecha_fin}
          onChange={(v) => guardar({ fecha_fin: v })}
        />
      </div>
      {vencido && (
        <p className="text-xs text-[color:var(--c-danger)]">
          ⏰ Venció el{' '}
          {new Date(project.fecha_fin + 'T00:00').toLocaleDateString('es-CO')}
        </p>
      )}
    </div>
  )
}

export default function Board() {
  const { id } = useParams()
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [nuevo, setNuevo] = useState('')
  const [abierta, setAbierta] = useState<Task | null>(null)
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  const cargar = () =>
    api.getProject(id!).then((p) => {
      setProject(p)
      setTasks(p.tasks)
    })

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const onDragEnd = (e: DragEndEvent) => {
    const taskId = String(e.active.id)
    const nuevoEstado = e.over ? String(e.over.id) : null
    if (!nuevoEstado) return
    const task = tasks.find((t) => t.id === taskId)
    if (!task || task.estado === nuevoEstado) return
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, estado: nuevoEstado } : t))
    )
    api.updateTaskEstado(taskId, nuevoEstado).then(cargar).catch(cargar)
  }

  const crearTarea = async (e: FormEvent) => {
    e.preventDefault()
    if (!nuevo.trim()) return
    await api.createTask(nuevo.trim(), id!)
    setNuevo('')
    cargar()
  }

  if (!project) return <p className="text-faint">Cargando…</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/proyectos" className="text-muted hover:text-ink text-sm">
          ← Proyectos
        </Link>
        <h2 className="font-serif text-2xl">{project.nombre}</h2>
      </div>

      <ProjectHeader project={project} onCambio={cargar} />

      <form onSubmit={crearTarea} className="flex gap-2 max-w-xl">
        <input
          value={nuevo}
          onChange={(e) => setNuevo(e.target.value)}
          placeholder="Nueva tarea…"
          className="input flex-1"
        />
        <button className="btn">Añadir</button>
      </form>

      <DndContext sensors={sensors} onDragEnd={onDragEnd}>
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNAS.map((c) => (
            <Column
              key={c.estado}
              estado={c.estado}
              titulo={c.titulo}
              tasks={tasks.filter((t) => t.estado === c.estado)}
              onAbrir={setAbierta}
            />
          ))}
        </div>
      </DndContext>

      <div className="pt-4 border-t border-line max-w-2xl">
        <h3 className="eyebrow mb-2">Notas del proyecto</h3>
        <NotasVinculadas
          entidadTipo="project"
          entidadId={project.id}
          placeholder="Nueva nota para el proyecto…"
        />
      </div>

      {abierta && (
        <TaskEditor
          taskInicial={abierta}
          onClose={() => {
            setAbierta(null)
            cargar()
          }}
        />
      )}
    </div>
  )
}

function Fecha({
  label,
  value,
  onChange,
}: {
  label: string
  value: string | null
  onChange: (v: string | null) => void
}) {
  return (
    <label className="text-xs text-muted flex flex-col gap-1">
      {label}
      <input
        type="date"
        min="2000-01-01"
        max="9999-12-31"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        className="input py-1.5"
      />
    </label>
  )
}

export function TaskEditor({
  taskInicial,
  onClose,
}: {
  taskInicial: Task
  onClose: () => void
}) {
  const [task, setTask] = useState<Task>(taskInicial)
  const [titulo, setTitulo] = useState(taskInicial.titulo)
  const [desc, setDesc] = useState(taskInicial.descripcion ?? '')
  const [notas, setNotas] = useState(taskInicial.notas ?? '')
  const [nuevoItem, setNuevoItem] = useState('')

  const guardar = async (patch: Record<string, unknown>) => {
    setTask(await api.updateTask(task.id, patch))
  }
  const addItem = async () => {
    if (!nuevoItem.trim()) return
    setTask(await api.addChecklistItem(task.id, nuevoItem.trim()))
    setNuevoItem('')
  }
  const toggle = async (itemId: string, hecho: boolean) =>
    setTask(await api.toggleChecklistItem(itemId, hecho))
  const delItem = async (itemId: string) =>
    setTask(await api.deleteChecklistItem(itemId))
  const delTask = async () => {
    if (!window.confirm('¿Eliminar esta tarea?')) return
    await api.deleteTask(task.id)
    onClose()
  }
  const hoy = () => {
    const d = new Date()
    const p = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
  }
  const completar = async () => {
    let t = await api.completeTask(task.id)
    if (!t.fecha_fin_real) t = await api.updateTask(task.id, { fecha_fin_real: hoy() })
    setTask(t)
  }
  const reabrir = async () =>
    setTask(await api.updateTask(task.id, { estado: 'en_ejecucion' }))

  const done = task.checklist.filter((i) => i.hecho).length

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-lg max-h-[85vh] overflow-y-auto p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <input
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            onBlur={() => titulo.trim() && guardar({ titulo: titulo.trim() })}
            className="flex-1 bg-transparent font-serif text-xl outline-none"
          />
          <button onClick={onClose} className="text-faint hover:text-ink">
            ✕
          </button>
        </div>

        <div className="flex items-center gap-3 text-sm">
          <span className="pill pill-mute">{task.estado}</span>
          <span className="text-muted">{task.avance_pct}% avance</span>
          {task.estado === 'terminada' ? (
            <button onClick={reabrir} className="btn-ghost btn ml-auto text-sm py-1.5">
              Reabrir
            </button>
          ) : (
            <button
              onClick={completar}
              className="btn ml-auto text-sm py-1.5"
              style={{ background: 'var(--c-green)', color: '#fff' }}
            >
              Marcar completada
            </button>
          )}
        </div>

        <label className="text-xs text-muted flex flex-wrap items-center gap-2">
          Recurrencia
          <select
            value={task.recurrencia ?? ''}
            onChange={(e) => guardar({ recurrencia: e.target.value || null })}
            className="input w-auto py-1 text-sm"
          >
            {RECURRENCIAS.map((r) => (
              <option key={r.v} value={r.v}>
                {r.label}
              </option>
            ))}
          </select>
          {task.recurrencia && (
            <span className="text-faint">
              Al completarla vuelve el siguiente periodo (avanza el fin planeado).
            </span>
          )}
        </label>

        <label className="text-xs text-muted flex flex-col gap-1">
          Descripción
          <textarea
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            onBlur={() => guardar({ descripcion: desc.trim() || null })}
            rows={3}
            placeholder="¿De qué trata la tarea?"
            className="input text-sm"
          />
        </label>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Fecha
            label="Inicio planeado"
            value={task.fecha_inicio_plan}
            onChange={(v) => guardar({ fecha_inicio_plan: v })}
          />
          <Fecha
            label="Fin planeado"
            value={task.fecha_limite}
            onChange={(v) => guardar({ fecha_limite: v })}
          />
          <Fecha
            label="Inicio real"
            value={task.fecha_inicio_real}
            onChange={(v) => guardar({ fecha_inicio_real: v })}
          />
          <Fecha
            label="Fin real"
            value={task.fecha_fin_real}
            onChange={(v) => guardar({ fecha_fin_real: v })}
          />
        </div>

        <div className="space-y-2">
          <div className="text-sm font-medium">
            Checklist{' '}
            {task.checklist.length > 0 && (
              <span className="text-faint font-normal">
                ({done}/{task.checklist.length})
              </span>
            )}
          </div>
          {task.checklist.map((i) => (
            <div key={i.id} className="group flex items-center gap-2">
              <input
                type="checkbox"
                checked={i.hecho}
                onChange={() => toggle(i.id, !i.hecho)}
                className="size-4 accent-[color:var(--c-teal)]"
              />
              <span className={i.hecho ? 'line-through text-faint' : ''}>
                {i.texto}
              </span>
              <button
                onClick={() => delItem(i.id)}
                className="ml-auto opacity-0 group-hover:opacity-100 text-faint hover:text-[color:var(--c-danger)] text-sm"
              >
                ✕
              </button>
            </div>
          ))}
          <div className="flex gap-2">
            <input
              value={nuevoItem}
              onChange={(e) => setNuevoItem(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addItem()}
              placeholder="Nuevo ítem…"
              className="input flex-1 text-sm py-1.5"
            />
            <button onClick={addItem} className="btn-ghost btn text-sm py-1.5">
              + Añadir
            </button>
          </div>
        </div>

        <label className="text-xs text-muted flex flex-col gap-1">
          Notas rápidas
          <textarea
            value={notas}
            onChange={(e) => setNotas(e.target.value)}
            onBlur={() => guardar({ notas: notas.trim() || null })}
            rows={2}
            placeholder="Apunte suelto que no amerita una hoja…"
            className="input text-sm"
          />
        </label>

        <NotasVinculadas
          entidadTipo="task"
          entidadId={task.id}
          placeholder="Nueva nota para esta tarea…"
        />

        <div className="pt-2 border-t border-line">
          <button
            onClick={delTask}
            className="text-faint hover:text-[color:var(--c-danger)] text-sm"
          >
            Eliminar tarea
          </button>
        </div>
      </div>
    </div>
  )
}

function NotasVinculadas({
  entidadTipo,
  entidadId,
  placeholder = 'Nueva nota…',
}: {
  entidadTipo: string
  entidadId: string
  placeholder?: string
}) {
  const [notas, setNotas] = useState<Note[]>([])
  const [titulo, setTitulo] = useState('')
  const [cuerpo, setCuerpo] = useState('')

  const cargar = () => api.linkedNotes(entidadTipo, entidadId).then(setNotas)
  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entidadTipo, entidadId])

  const crear = async () => {
    if (!cuerpo.trim()) return
    // Una sola petición: la nota nace ya vinculada (nunca queda huérfana).
    await api.createNote(
      cuerpo.trim(), null, titulo.trim() || null, entidadTipo, entidadId
    )
    setTitulo('')
    setCuerpo('')
    cargar()
  }
  const desvincular = async (id: string) => {
    await api.unlinkNote(id, entidadTipo, entidadId)
    cargar()
  }

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium">
        Notas vinculadas{' '}
        <span className="text-faint font-normal">(hojas · buscables)</span>
      </div>
      {notas.map((n) => (
        <NotaVinculada key={n.id} nota={n} onDesvincular={() => desvincular(n.id)} />
      ))}
      <div className="rounded-lg border border-dashed border-line p-2 space-y-2">
        <input
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
          placeholder="Título (opcional)"
          className="w-full bg-transparent text-sm outline-none placeholder:text-faint"
        />
        <div className="flex gap-2">
          <textarea
            value={cuerpo}
            onChange={(e) => setCuerpo(e.target.value)}
            placeholder={placeholder}
            rows={2}
            className="input flex-1 text-sm py-1.5"
          />
          <button onClick={crear} className="btn-ghost btn text-sm py-1.5 shrink-0">
            + Añadir
          </button>
        </div>
      </div>
    </div>
  )
}

function NotaVinculada({
  nota,
  onDesvincular,
}: {
  nota: Note
  onDesvincular: () => void
}) {
  const [titulo, setTitulo] = useState(nota.titulo ?? '')
  const [cuerpo, setCuerpo] = useState(nota.contenido)

  const guardar = () =>
    api.updateNote(nota.id, {
      titulo: titulo.trim() || null,
      contenido: cuerpo.trim(),
    })

  return (
    <div className="group rounded-lg border border-line bg-surface-2 p-2.5">
      <div className="flex items-center gap-2">
        <input
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
          onBlur={guardar}
          placeholder="Sin título"
          className="flex-1 bg-transparent text-sm font-medium outline-none placeholder:text-faint"
        />
        <button
          onClick={onDesvincular}
          title="Desvincular (no borra la hoja)"
          className="opacity-0 group-hover:opacity-100 text-faint hover:text-[color:var(--c-danger)] text-xs transition"
        >
          desvincular
        </button>
      </div>
      <textarea
        value={cuerpo}
        onChange={(e) => setCuerpo(e.target.value)}
        onBlur={guardar}
        rows={2}
        className="w-full mt-1 bg-transparent text-sm text-muted outline-none resize-none"
      />
    </div>
  )
}
