"""Lógica de negocio del registro de tiempo.

Regla central: UNA sola sesión corriendo a la vez (solo se hace una cosa a la
vez). Iniciar una nueva cierra la anterior en ese instante. Inicio y fin son
editables después, porque la gente olvida parar el reloj.
"""

import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.projects import Project
from app.models.tasks import Task
from app.models.time_entries import TimeEntry
from app.schemas.time_entries import TimeEntryStart, TimeEntryUpdate
from app.timeutils import now_local, zona


def _enriquecer(db: Session, entry: TimeEntry) -> TimeEntry:
    task = db.get(Task, entry.task_id)
    entry.tarea = task.titulo if task else None  # type: ignore[attr-defined]
    proyecto = db.get(Project, task.project_id) if task and task.project_id else None
    entry.proyecto = proyecto.nombre if proyecto else None  # type: ignore[attr-defined]
    entry.project_id = task.project_id if task else None  # type: ignore[attr-defined]
    return entry


def current_entry(db: Session) -> TimeEntry | None:
    entry = db.execute(
        select(TimeEntry).where(TimeEntry.fin.is_(None)).order_by(TimeEntry.inicio.desc())
    ).scalars().first()
    return _enriquecer(db, entry) if entry else None


def start_entry(db: Session, data: TimeEntryStart) -> TimeEntry:
    if db.get(Task, data.task_id) is None:
        raise ValueError("La tarea no existe")
    ahora = now_local()
    # Cierra cualquier sesión corriendo: empezar algo nuevo es dejar lo anterior.
    db.execute(
        TimeEntry.__table__.update()
        .where(TimeEntry.fin.is_(None))
        .values(fin=ahora)
    )
    entry = TimeEntry(task_id=data.task_id, inicio=ahora, nota=data.nota)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _enriquecer(db, entry)


def stop_entry(db: Session) -> TimeEntry | None:
    """Cierra la sesión corriendo; None si no hay ninguna."""
    entry = db.execute(
        select(TimeEntry).where(TimeEntry.fin.is_(None))
    ).scalars().first()
    if entry is None:
        return None
    entry.fin = now_local()
    db.commit()
    db.refresh(entry)
    return _enriquecer(db, entry)


def list_entries(db: Session, dia: date | None = None) -> list[TimeEntry]:
    """Sesiones de un día (hoy por defecto), la más reciente primero.
    Una sesión pertenece al día en que EMPEZÓ."""
    dia = dia or now_local().date()
    tz = zona()
    desde = datetime.combine(dia, time.min, tzinfo=tz)
    hasta = desde + timedelta(days=1)
    entries = db.execute(
        select(TimeEntry)
        .where(TimeEntry.inicio >= desde, TimeEntry.inicio < hasta)
        .order_by(TimeEntry.inicio.desc())
    ).scalars().all()
    return [_enriquecer(db, e) for e in entries]


def update_entry(
    db: Session, entry_id: uuid.UUID, data: TimeEntryUpdate
) -> TimeEntry | None:
    entry = db.get(TimeEntry, entry_id)
    if entry is None:
        return None
    cambios = data.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(entry, campo, valor)
    if entry.fin is not None and entry.fin <= entry.inicio:
        raise ValueError("El fin debe ser posterior al inicio")
    db.commit()
    db.refresh(entry)
    return _enriquecer(db, entry)


def delete_entry(db: Session, entry_id: uuid.UUID) -> bool:
    entry = db.get(TimeEntry, entry_id)
    if entry is None:
        return False
    db.delete(entry)
    db.commit()
    return True
