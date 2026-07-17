"""Lógica de negocio del dominio de proyectos."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.projects import Project
from app.schemas.projects import ProjectCreate, ProjectUpdate

TERMINADO = "terminado"


def create_project(db: Session, data: ProjectCreate) -> Project:
    project = Project(
        nombre=data.nombre,
        descripcion=data.descripcion,
        estado=data.estado.value,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: uuid.UUID) -> Project | None:
    """Proyecto con sus tareas cargadas (las notas las agrega el router)."""
    stmt = (
        select(Project)
        .options(selectinload(Project.tasks))
        .where(Project.id == project_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_projects(db: Session, estado: str | None = None) -> list[Project]:
    stmt = select(Project)
    if estado is not None:
        stmt = stmt.where(Project.estado == estado)
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
