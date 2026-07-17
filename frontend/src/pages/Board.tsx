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

// Orden convencional de Kanban. (El spec deja el orden configurable a futuro.)
const COLUMNAS = [
  { estado: 'planeada', titulo: 'Planeada' },
  { estado: 'en_ejecucion', titulo: 'En ejecución' },
  { estado: 'en_pausa', titulo: 'En pausa' },
  { estado: 'terminada', titulo: 'Terminada' },
]

function Card({ task }: { task: Task }) {
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
      className={`rounded-lg border border-slate-700 bg-slate-800 p-3 cursor-grab active:cursor-grabbing ${
        isDragging ? 'opacity-50' : ''
      }`}
    >
      <div className="text-sm">{task.titulo}</div>
      {task.avance_pct > 0 && (
        <div className="mt-2 h-1 rounded bg-slate-700 overflow-hidden">
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
}: {
  estado: string
  titulo: string
  tasks: Task[]
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
          <Card key={t.id} task={t} />
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
    // Optimista: mueve la tarjeta ya; revierte si la API falla.
    setTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, estado: nuevoEstado } : t))
    )
    api.updateTaskEstado(taskId, nuevoEstado).catch(() => cargar())
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
        <Link
          to="/proyectos"
          className="text-slate-400 hover:text-slate-200 text-sm"
        >
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
              <li key={n.id}>• {n.contenido}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
