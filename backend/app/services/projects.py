"""Lógica de negocio del dominio de proyectos."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.notebooks import Notebook
from app.models.portfolios import Portfolio
from app.models.projects import Project
from app.models.tasks import Task
from app.schemas.projects import ProjectCreate, ProjectUpdate

TERMINADO = "terminado"  # estado de PROYECTO
TAREA_TERMINADA = "terminada"  # estado de TAREA

# Centinela para distinguir "sin portafolio" (None) de "sin filtro".
_SIN_FILTRO = object()


def _adjuntar_avance(project: Project, total: int, terminadas: int) -> Project:
    """Adjunta los derivados de tareas para que el schema los serialice."""
    project.total_tareas = total  # type: ignore[attr-defined]
    project.tareas_terminadas = terminadas  # type: ignore[attr-defined]
    project.avance = (  # type: ignore[attr-defined]
        round(terminadas / total * 100) if total else None
    )
    return project


def _conteos_por_proyecto(
    db: Session, ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, int]]:
    """{project_id: (total_tareas, terminadas)} en una sola consulta."""
    if not ids:
        return {}
    filas = db.execute(
        select(
            Task.project_id,
            func.count(Task.id),
            func.count(Task.id).filter(Task.estado == TAREA_TERMINADA),
        )
        .where(Task.project_id.in_(ids))
        .group_by(Task.project_id)
    ).all()
    return {pid: (total, term) for pid, total, term in filas}


def _validar_portafolio(db: Session, portfolio_id: uuid.UUID | None) -> None:
    if portfolio_id is not None and db.get(Portfolio, portfolio_id) is None:
        raise ValueError("El portafolio indicado no existe")


def proyecto_personal(db: Session) -> Project:
    """El proyecto «Personal» del inquilino (lo crea si no existe). Las tareas
    creadas sin proyecto caen aquí."""
    p = db.execute(
        select(Project).where(Project.es_personal.is_(True))
    ).scalars().first()
    if p is None:
        p = Project(nombre="Personal", es_personal=True)
        db.add(p)
        db.flush()
    return p


def _renombrar_cuaderno(db: Session, nombre_viejo: str, nombre_nuevo: str) -> None:
    """Mantiene el cuaderno homónimo del proyecto en sincronía con su nombre."""
    nb = db.execute(
        select(Notebook).where(func.lower(Notebook.nombre) == nombre_viejo.lower())
    ).scalar_one_or_none()
    if nb is None:
        return
    ya_existe = db.execute(
        select(Notebook.id).where(
            func.lower(Notebook.nombre) == nombre_nuevo.lower(),
            Notebook.id != nb.id,
        )
    ).first()
    if ya_existe is None:  # evita chocar con otro cuaderno ya llamado así
        nb.nombre = nombre_nuevo


def create_project(db: Session, data: ProjectCreate) -> Project:
    _validar_portafolio(db, data.portfolio_id)
    project = Project(
        nombre=data.nombre,
        descripcion=data.descripcion,
        estado=data.estado.value,
        portfolio_id=data.portfolio_id,
        fecha_inicio=data.fecha_inicio,
        fecha_fin=data.fecha_fin,
    )
    db.add(project)
    db.flush()
    # El cuaderno del proyecto nace con el proyecto (no con la primera nota):
    # así aparece de una vez como destino al guardar notas.
    from app.services.notes import cuaderno_de_proyecto

    cuaderno_de_proyecto(db, project)
    db.commit()
    db.refresh(project)
    return _adjuntar_avance(project, 0, 0)


def get_project(db: Session, project_id: uuid.UUID) -> Project | None:
    """Proyecto con sus tareas cargadas (las notas las agrega el router)."""
    stmt = (
        select(Project)
        .options(
            selectinload(Project.tasks).selectinload(Task.checklist),
            selectinload(Project.tasks).selectinload(Task.project),
        )
        .where(Project.id == project_id)
    )
    project = db.execute(stmt).scalar_one_or_none()
    if project is not None:
        total = len(project.tasks)
        terminadas = sum(1 for t in project.tasks if t.estado == TAREA_TERMINADA)
        _adjuntar_avance(project, total, terminadas)
    return project


def list_projects(
    db: Session,
    estado: str | None = None,
    portfolio_id: uuid.UUID | None | object = _SIN_FILTRO,
) -> list[Project]:
    """Lista proyectos. Filtra por estado y/o portafolio (None = solo los sin
    portafolio)."""
    stmt = select(Project)
    if estado is not None:
        stmt = stmt.where(Project.estado == estado)
    if portfolio_id is not _SIN_FILTRO:
        stmt = stmt.where(Project.portfolio_id == portfolio_id)
    stmt = stmt.order_by(Project.nombre)
    proyectos = list(db.execute(stmt).scalars().all())
    conteos = _conteos_por_proyecto(db, [p.id for p in proyectos])
    for p in proyectos:
        total, term = conteos.get(p.id, (0, 0))
        _adjuntar_avance(p, total, term)
    return proyectos


def update_project(
    db: Session, project_id: uuid.UUID, data: ProjectUpdate
) -> Project | None:
    project = db.get(Project, project_id)
    if project is None:
        return None
    cambios = data.model_dump(exclude_unset=True)
    if cambios.get("estado") is not None:
        cambios["estado"] = cambios["estado"].value
    if "portfolio_id" in cambios:
        _validar_portafolio(db, cambios["portfolio_id"])
    nombre_viejo = project.nombre
    for campo, valor in cambios.items():
        setattr(project, campo, valor)
    nombre_nuevo = cambios.get("nombre")
    if nombre_nuevo and nombre_nuevo != nombre_viejo:
        _renombrar_cuaderno(db, nombre_viejo, nombre_nuevo)
    db.commit()
    db.refresh(project)
    total, term = _conteos_por_proyecto(db, [project.id]).get(project.id, (0, 0))
    return _adjuntar_avance(project, total, term)


def archive_project(db: Session, project_id: uuid.UUID) -> Project | None:
    """Archivar = pasar a estado terminado."""
    project = db.get(Project, project_id)
    if project is None:
        return None
    project.estado = TERMINADO
    db.commit()
    db.refresh(project)
    total, term = _conteos_por_proyecto(db, [project.id]).get(project.id, (0, 0))
    return _adjuntar_avance(project, total, term)
