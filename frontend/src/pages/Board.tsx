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
import { api, type ProjectDetail, type Task } from '../api'

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
      className={`rounded-lg border border-slate-700 bg-slate-800 p-3 cursor-pointer active:cursor-grabbing ${
        isDragging ? 'opacity-50' : ''
      }`}
    >
      <div className="text-sm">{task.titulo}</div>
      {task.checklist.length > 0 && (
        <div className="text-xs text-slate-400 mt-1.5">
          ☑ {hechos(task)}/{task.checklist.length}
        </div>
      )}
      {task.avance_pct > 0 && (
        <div className="mt-1.5 h-1 rounded bg-slate-700 overflow-hidden">
          <div
            className="h-full bg-indigo-500"
            style={{ width: `${task.avance_pct}%` }}
          />
        </div>
      )}
      {task.fecha_limite && (
        <div className="text-xs text-slate-500 mt-1.5">
          vence {task.fecha_limite}
        </div>
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
          ? 'border-indigo-500 bg-indigo-500/5'
          : 'border-slate-800 bg-slate-900/40'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium">{titulo}</span>
        <span className="text-xs text-slate-500">{tasks.length}</span>
      </div>
      <div className="space-y-2 min-h-16">
        {tasks.map((t) => (
          <Card key={t.id} task={t} onAbrir={onAbrir} />
        ))}
      </div>
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

  if (!project) return <p className="text-slate-500">Cargando…</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/proyectos" className="text-slate-400 hover:text-slate-200 text-sm">
          ← Proyectos
        </Link>
        <h2 className="text-xl font-semibold">{project.nombre}</h2>
      </div>

      <form onSubmit={crearTarea} className="flex gap-2 max-w-xl">
        <input
          value={nuevo}
          onChange={(e) => setNuevo(e.target.value)}
          placeholder="Nueva tarea…"
          className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-4 py-2.5 outline-none focus:border-indigo-500"
        />
        <button className="rounded-lg bg-indigo-600 hover:bg-indigo-500 px-4 font-medium">
          Añadir
        </button>
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

      {project.notes.length > 0 && (
        <div className="pt-4 border-t border-slate-800">
          <h3 className="text-sm font-medium text-slate-400 mb-2">
            Notas del proyecto
          </h3>
          <ul className="space-y-1 text-sm text-slate-300">
            {project.notes.map((n) => (
              <li key={n.id}>• {n.titulo || n.contenido}</li>
            ))}
          </ul>
        </div>
      )}

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
    <label className="text-xs text-slate-400 flex flex-col gap-1">
      {label}
      <input
        type="date"
        min="2000-01-01"
        max="9999-12-31"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        className="rounded-lg bg-slate-950 border border-slate-700 px-2 py-1.5 text-slate-100 outline-none focus:border-indigo-500"
      />
    </label>
  )
}

function TaskEditor({
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
        className="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-xl border border-slate-700 bg-slate-900 p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <input
            value={titulo}
            onChange={(e) => setTitulo(e.target.value)}
            onBlur={() => titulo.trim() && guardar({ titulo: titulo.trim() })}
            className="flex-1 bg-transparent text-lg font-semibold outline-none"
          />
          <button onClick={onClose} className="text-slate-500 hover:text-slate-200">
            ✕
          </button>
        </div>

        <div className="flex items-center gap-3 text-sm">
          <span className="rounded px-2 py-0.5 bg-slate-800 text-slate-300">
            {task.estado}
          </span>
          <span className="text-slate-400">{task.avance_pct}% avance</span>
          {task.estado === 'terminada' ? (
            <button
              onClick={reabrir}
              className="ml-auto rounded-lg border border-slate-700 px-3 py-1 hover:bg-slate-800"
            >
              Reabrir
            </button>
          ) : (
            <button
              onClick={completar}
              className="ml-auto rounded-lg bg-emerald-600/80 hover:bg-emerald-600 px-3 py-1 font-medium"
            >
              Marcar completada
            </button>
          )}
        </div>

        <label className="text-xs text-slate-400 flex flex-col gap-1">
          Descripción
          <textarea
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
            onBlur={() => guardar({ descripcion: desc.trim() || null })}
            rows={3}
            placeholder="¿De qué trata la tarea?"
            className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-slate-100 outline-none focus:border-indigo-500"
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
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
          <div className="text-sm font-medium text-slate-300">
            Checklist{' '}
            {task.checklist.length > 0 && (
              <span className="text-slate-500 font-normal">
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
                className="size-4 accent-indigo-500"
              />
              <span className={i.hecho ? 'line-through text-slate-500' : ''}>
                {i.texto}
              </span>
              <button
                onClick={() => delItem(i.id)}
                className="ml-auto opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 text-sm"
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
              className="flex-1 rounded-lg bg-slate-950 border border-slate-700 px-3 py-1.5 text-sm outline-none focus:border-indigo-500"
            />
            <button
              onClick={addItem}
              className="rounded-lg border border-slate-700 px-3 text-sm hover:bg-slate-800"
            >
              + Añadir
            </button>
          </div>
        </div>

        <label className="text-xs text-slate-400 flex flex-col gap-1">
          Notas
          <textarea
            value={notas}
            onChange={(e) => setNotas(e.target.value)}
            onBlur={() => guardar({ notas: notas.trim() || null })}
            rows={3}
            placeholder="Apuntes, avances, recordatorios…"
            className="rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-sm text-slate-100 outline-none focus:border-indigo-500"
          />
        </label>

        <div className="pt-2 border-t border-slate-800">
          <button
            onClick={delTask}
            className="text-slate-500 hover:text-red-400 text-sm"
          >
            Eliminar tarea
          </button>
        </div>
      </div>
    </div>
  )
}
