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
    entry = TimeEntry(
        task_id=data.task_id, inicio=ahora, nota=data.nota, aviso_min=data.aviso_min
    )
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


def month_summary(db: Session, anio: int, mes: int) -> dict:
    """Consolidado del mes: total, por tarea, por proyecto y por día.
    Las sesiones corriendo cuentan hasta ahora. Minutos redondeados."""
    tz = zona()
    desde = datetime(anio, mes, 1, tzinfo=tz)
    hasta = (
        datetime(anio + 1, 1, 1, tzinfo=tz)
        if mes == 12
        else datetime(anio, mes + 1, 1, tzinfo=tz)
    )
    entries = db.execute(
        select(TimeEntry).where(TimeEntry.inicio >= desde, TimeEntry.inicio < hasta)
    ).scalars().all()

    ahora = now_local()
    por_tarea: dict[str, dict] = {}
    por_proyecto: dict[str, int] = {}
    por_dia: dict[int, int] = {}
    total = 0
    for e in entries:
        _enriquecer(db, e)
        fin = e.fin or ahora
        minutos = max(0, round((fin - e.inicio).total_seconds() / 60))
        total += minutos
        tarea = e.tarea or "(tarea eliminada)"  # type: ignore[attr-defined]
        proyecto = e.proyecto or "(sin proyecto)"  # type: ignore[attr-defined]
        fila = por_tarea.setdefault(
            tarea, {"tarea": tarea, "proyecto": proyecto, "min": 0}
        )
        fila["min"] += minutos
        por_proyecto[proyecto] = por_proyecto.get(proyecto, 0) + minutos
        dia = e.inicio.astimezone(tz).day
        por_dia[dia] = por_dia.get(dia, 0) + minutos

    return {
        "anio": anio,
        "mes": mes,
        "total_min": total,
        "dias_activos": len(por_dia),
        "por_tarea": sorted(por_tarea.values(), key=lambda f: -f["min"]),
        "por_proyecto": [
            {"proyecto": p, "min": m}
            for p, m in sorted(por_proyecto.items(), key=lambda kv: -kv[1])
        ],
        "por_dia": [
            {"dia": d, "min": m} for d, m in sorted(por_dia.items())
        ],
    }


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
