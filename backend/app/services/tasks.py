"""Lógica de negocio del dominio de tareas.

No conoce HTTP ni el canal. Señala errores de referencia cruzada (proyecto
inexistente) con ValueError, que el router traduce a 400.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.projects import Project
from app.models.tasks import Task
from app.schemas.tasks import TaskCreate, TaskUpdate

TERMINADA = "terminada"


def _validar_proyecto(db: Session, project_id: uuid.UUID | None) -> None:
    if project_id is not None and db.get(Project, project_id) is None:
        raise ValueError("El proyecto indicado no existe")


def create_task(db: Session, data: TaskCreate) -> Task:
    _validar_proyecto(db, data.project_id)
    task = Task(
        titulo=data.titulo,
        project_id=data.project_id,
        estado=data.estado.value,
        avance_pct=data.avance_pct,
        fecha_limite=data.fecha_limite,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: uuid.UUID) -> Task | None:
    return db.get(Task, task_id)


def list_tasks(
    db: Session,
    project_id: uuid.UUID | None = None,
    estado: str | None = None,
) -> list[Task]:
    stmt = select(Task)
    if project_id is not None:
        stmt = stmt.where(Task.project_id == project_id)
    if estado is not None:
        stmt = stmt.where(Task.estado == estado)
    stmt = stmt.order_by(Task.fecha_limite.is_(None), Task.fecha_limite)
    return list(db.execute(stmt).scalars().all())


def list_hoy(db: Session) -> list[Task]:
    """Tareas que vencen hoy o están vencidas y aún no terminadas.

    Pensado para alguien olvidadizo: incluye lo atrasado, no solo lo de hoy.
    Usa la fecha del servidor Postgres (current_date).
    """
    stmt = (
        select(Task)
        .where(
            Task.estado != TERMINADA,
            Task.fecha_limite.is_not(None),
            Task.fecha_limite <= func.current_date(),
        )
        .order_by(Task.fecha_limite)
    )
    return list(db.execute(stmt).scalars().all())


def list_pendientes(db: Session) -> list[Task]:
    """Todo lo que no está terminado."""
    stmt = (
        select(Task)
        .where(Task.estado != TERMINADA)
        .order_by(Task.fecha_limite.is_(None), Task.fecha_limite)
    )
    return list(db.execute(stmt).scalars().all())


def update_task(db: Session, task_id: uuid.UUID, data: TaskUpdate) -> Task | None:
    task = db.get(Task, task_id)
    if task is None:
        return None
    # Solo los campos realmente enviados (permite null explícito p. ej. en
    # project_id / fecha_limite sin pisar el resto).
    cambios = data.model_dump(exclude_unset=True)
    if "project_id" in cambios:
        _validar_proyecto(db, cambios["project_id"])
    if cambios.get("estado") is not None:
        cambios["estado"] = cambios["estado"].value
    for campo, valor in cambios.items():
        setattr(task, campo, valor)
    db.commit()
    db.refresh(task)
    return task


def set_progress(db: Session, task_id: uuid.UUID, avance_pct: int) -> Task | None:
    """Marca avance (solo el porcentaje; no cambia el estado)."""
    task = db.get(Task, task_id)
    if task is None:
        return None
    task.avance_pct = avance_pct
    db.commit()
    db.refresh(task)
    return task


def complete_task(db: Session, task_id: uuid.UUID) -> Task | None:
    """Marca completada: estado terminada y avance 100%."""
    task = db.get(Task, task_id)
    if task is None:
        return None
    task.estado = TERMINADA
    task.avance_pct = 100
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
