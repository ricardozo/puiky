"""Lógica de negocio del dominio de tareas y su checklist.

No conoce HTTP ni el canal. Señala errores de referencia cruzada (proyecto
inexistente) con ValueError, que el router traduce a 400.

Avance: si la tarea tiene checklist, `avance_pct` se calcula = hechos/total y la
tarea se auto-completa al 100% (y vuelve a en_ejecucion si se desmarca algo). Sin
checklist, `avance_pct` es manual.
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.projects import Project
from app.models.tasks import ChecklistItem, Task
from app.schemas.tasks import ChecklistItemCreate, ChecklistItemUpdate, TaskCreate, TaskUpdate
from app.services.projects import proyecto_personal
from app.services.recurrence import siguiente_vencimiento

TERMINADA = "terminada"
EN_EJECUCION = "en_ejecucion"
PLANEADA = "planeada"


def _reciclar(task: Task) -> None:
    """Tarea recurrente completada: reinicia y avanza la fecha límite al
    siguiente periodo (desde la fecha límite, o desde hoy si no tenía)."""
    base = task.fecha_limite or date.today()
    task.fecha_limite = siguiente_vencimiento(base, task.recurrencia)
    task.estado = PLANEADA
    task.avance_pct = 0
    task.fecha_inicio_real = None
    task.fecha_fin_real = None
    for item in task.checklist:
        item.hecho = False


def _completar(task: Task) -> None:
    """Completa una tarea: si es recurrente, la recicla; si no, la termina."""
    if task.recurrencia:
        _reciclar(task)
    else:
        task.estado = TERMINADA
        task.avance_pct = 100


def _validar_proyecto(db: Session, project_id: uuid.UUID | None) -> None:
    if project_id is not None and db.get(Project, project_id) is None:
        raise ValueError("El proyecto indicado no existe")


def _con_checklist(stmt):
    return stmt.options(
        selectinload(Task.checklist), selectinload(Task.project)
    )


def _aplicar_progreso_checklist(task: Task) -> None:
    """Recalcula avance desde el checklist y auto-completa. Solo si hay ítems."""
    items = task.checklist
    if not items:
        return
    total = len(items)
    hechos = sum(1 for i in items if i.hecho)
    if hechos == total:
        _completar(task)  # recicla si es recurrente, o termina
    else:
        task.avance_pct = round(hechos / total * 100)
        if task.estado == TERMINADA:
            task.estado = EN_EJECUCION


def create_task(db: Session, data: TaskCreate) -> Task:
    _validar_proyecto(db, data.project_id)
    # Sin proyecto explícito, la tarea cae en el proyecto «Personal».
    project_id = data.project_id or proyecto_personal(db).id
    task = Task(
        titulo=data.titulo,
        descripcion=data.descripcion,
        notas=data.notas,
        project_id=project_id,
        estado=data.estado.value,
        avance_pct=data.avance_pct,
        fecha_limite=data.fecha_limite,
        fecha_inicio_plan=data.fecha_inicio_plan,
        fecha_inicio_real=data.fecha_inicio_real,
        fecha_fin_real=data.fecha_fin_real,
        recurrencia=data.recurrencia,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: uuid.UUID) -> Task | None:
    return db.execute(
        _con_checklist(select(Task).where(Task.id == task_id))
    ).scalar_one_or_none()


def list_tasks(
    db: Session,
    project_id: uuid.UUID | None = None,
    estado: str | None = None,
    q: str | None = None,
) -> list[Task]:
    """Lista tareas ordenadas por vencimiento (las sin fecha, al final). Filtra
    por proyecto, estado y/o texto en el título (`q`)."""
    stmt = select(Task)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if estado is not None:
        stmt = stmt.where(Task.estado == estado)
    if q:
        stmt = stmt.where(Task.titulo.ilike(f"%{q}%"))
    stmt = stmt.order_by(Task.fecha_limite.is_(None), Task.fecha_limite)
    return list(db.execute(_con_checklist(stmt)).scalars().all())


def list_hoy(db: Session) -> list[Task]:
    """Tareas cuyo fin planeado es hoy o ya pasó y no están terminadas."""
    stmt = (
        select(Task)
        .where(
            Task.estado != TERMINADA,
            Task.fecha_limite.is_not(None),
            Task.fecha_limite <= func.current_date(),
        )
        .order_by(Task.fecha_limite)
    )
    return list(db.execute(_con_checklist(stmt)).scalars().all())


def list_pendientes(db: Session) -> list[Task]:
    """Todo lo que no está terminado."""
    stmt = (
        select(Task)
        .where(Task.estado != TERMINADA)
        .order_by(Task.fecha_limite.is_(None), Task.fecha_limite)
    )
    return list(db.execute(_con_checklist(stmt)).scalars().all())


def list_recurrentes_pendientes(db: Session) -> list[Task]:
    """Tareas recurrentes sin terminar, por vencimiento (las sin fecha, al final)."""
    stmt = (
        select(Task)
        .where(Task.estado != TERMINADA, Task.recurrencia.is_not(None))
        .order_by(Task.fecha_limite.is_(None), Task.fecha_limite)
    )
    return list(db.execute(_con_checklist(stmt)).scalars().all())


def update_task(db: Session, task_id: uuid.UUID, data: TaskUpdate) -> Task | None:
    task = get_task(db, task_id)
    if task is None:
        return None
    cambios = data.model_dump(exclude_unset=True)
    if "project_id" in cambios:
        _validar_proyecto(db, cambios["project_id"])
    if cambios.get("estado") is not None:
        cambios["estado"] = cambios["estado"].value
    for campo, valor in cambios.items():
        setattr(task, campo, valor)
    # Coherencia de avance con el estado / checklist:
    if cambios.get("estado") == TERMINADA:
        _completar(task)  # recicla si es recurrente, o fija avance 100
    elif "estado" in cambios:
        _aplicar_progreso_checklist(task)  # recalcula desde checklist si lo hay
    db.commit()
    db.refresh(task)
    return task


def set_progress(db: Session, task_id: uuid.UUID, avance_pct: int) -> Task | None:
    """Marca avance manual (solo tiene sentido en tareas sin checklist)."""
    task = get_task(db, task_id)
    if task is None:
        return None
    task.avance_pct = avance_pct
    db.commit()
    db.refresh(task)
    return task


def complete_task(db: Session, task_id: uuid.UUID) -> Task | None:
    """Completa la tarea. Si es recurrente, la reinicia y avanza su fecha límite;
    si no, la marca terminada al 100%."""
    task = get_task(db, task_id)
    if task is None:
        return None
    _completar(task)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: uuid.UUID) -> bool:
    task = db.get(Task, task_id)
    if task is None:
        return False
    db.delete(task)
    db.commit()
    return True


# --- Checklist ---


def add_checklist_item(
    db: Session, task_id: uuid.UUID, data: ChecklistItemCreate
) -> Task | None:
    task = get_task(db, task_id)
    if task is None:
        return None
    orden = (max((i.orden for i in task.checklist), default=-1)) + 1
    task.checklist.append(
        ChecklistItem(texto=data.texto, orden=orden)
    )
    _aplicar_progreso_checklist(task)
    db.commit()
    db.refresh(task)
    return task


def update_checklist_item(
    db: Session, item_id: uuid.UUID, data: ChecklistItemUpdate
) -> Task | None:
    item = db.get(ChecklistItem, item_id)
    if item is None:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(item, campo, valor)
    task = get_task(db, item.task_id)
    assert task is not None
    _aplicar_progreso_checklist(task)
    db.commit()
    db.refresh(task)
    return task


def delete_checklist_item(db: Session, item_id: uuid.UUID) -> Task | None:
    item = db.get(ChecklistItem, item_id)
    if item is None:
        return None
    task = get_task(db, item.task_id)
    assert task is not None
    # Quitar de la colección (delete-orphan lo borra) para que el checklist en
    # memoria quede consistente y el avance se recalcule bien.
    objetivo = next((i for i in task.checklist if i.id == item_id), None)
    if objetivo is not None:
        task.checklist.remove(objetivo)
    _aplicar_progreso_checklist(task)
    db.commit()
    db.refresh(task)
    return task
