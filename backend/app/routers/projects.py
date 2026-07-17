"""Endpoints HTTP del dominio de proyectos."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.projects import (
    ProjectCreate,
    ProjectDetailOut,
    ProjectEstado,
    ProjectOut,
    ProjectUpdate,
)
from app.services import notes as notes_service
from app.services import projects as service

router = APIRouter(prefix="/projects", tags=["proyectos"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def crear_proyecto(
    data: ProjectCreate, db: Session = Depends(get_db)
) -> ProjectOut:
    try:
        return service.create_project(db, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("", response_model=list[ProjectOut])
def listar_proyectos(
    estado: ProjectEstado | None = Query(default=None),
    portfolio_id: uuid.UUID | None = Query(default=None),
    sin_portafolio: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[ProjectOut]:
    """Lista proyectos. Filtra por `portfolio_id`, o `sin_portafolio=true` para
    los que no tienen portafolio; sin filtro, todos."""
    valor_estado = estado.value if estado is not None else None
    if sin_portafolio:
        return service.list_projects(db, valor_estado, portfolio_id=None)
    if portfolio_id is not None:
        return service.list_projects(db, valor_estado, portfolio_id=portfolio_id)
    return service.list_projects(db, valor_estado)


@router.get("/{project_id}", response_model=ProjectDetailOut)
def ver_proyecto(
    project_id: uuid.UUID, db: Session = Depends(get_db)
) -> ProjectDetailOut:
    """Devuelve el proyecto con sus tareas y sus notas vinculadas."""
    proyecto = service.get_project(db, project_id)
    if proyecto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")
    notas = notes_service.notes_for_entity(db, "project", project_id)
    return ProjectDetailOut(
        id=proyecto.id,
        nombre=proyecto.nombre,
        descripcion=proyecto.descripcion,
        estado=proyecto.estado,
        portfolio_id=proyecto.portfolio_id,
        tasks=proyecto.tasks,
        notes=notas,
    )


@router.put("/{project_id}", response_model=ProjectOut)
def editar_proyecto(
    project_id: uuid.UUID, data: ProjectUpdate, db: Session = Depends(get_db)
) -> ProjectOut:
    try:
        proyecto = service.update_project(db, project_id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if proyecto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")
    return proyecto


@router.post("/{project_id}/archive", response_model=ProjectOut)
def archivar_proyecto(
    project_id: uuid.UUID, db: Session = Depends(get_db)
) -> ProjectOut:
    """Archiva el proyecto (pasa a estado terminado)."""
    proyecto = service.archive_project(db, project_id)
    if proyecto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")
    return proyecto
