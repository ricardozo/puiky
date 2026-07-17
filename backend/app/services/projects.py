"""Lógica de negocio del dominio de proyectos."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.portfolios import Portfolio
from app.models.projects import Project
from app.models.tasks import Task
from app.schemas.projects import ProjectCreate, ProjectUpdate

TERMINADO = "terminado"

# Centinela para distinguir "sin portafolio" (None) de "sin filtro".
_SIN_FILTRO = object()


def _validar_portafolio(db: Session, portfolio_id: uuid.UUID | None) -> None:
    if portfolio_id is not None and db.get(Portfolio, portfolio_id) is None:
        raise ValueError("El portafolio indicado no existe")


def create_project(db: Session, data: ProjectCreate) -> Project:
    _validar_portafolio(db, data.portfolio_id)
    project = Project(
        nombre=data.nombre,
        descripcion=data.descripcion,
        estado=data.estado.value,
        portfolio_id=data.portfolio_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: uuid.UUID) -> Project | None:
    """Proyecto con sus tareas cargadas (las notas las agrega el router)."""
    stmt = (
        select(Project)
        .options(selectinload(Project.tasks).selectinload(Task.checklist))
        .where(Project.id == project_id)
    )
    return db.execute(stmt).scalar_one_or_none()


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
    return list(db.execute(stmt).scalars().all())


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
    for campo, valor in cambios.items():
        setattr(project, campo, valor)
    db.commit()
    db.refresh(project)
    return project


def archive_project(db: Session, project_id: uuid.UUID) -> Project | None:
    """Archivar = pasar a estado terminado."""
    project = db.get(Project, project_id)
    if project is None:
        return None
    project.estado = TERMINADO
    db.commit()
    db.refresh(project)
    return project
