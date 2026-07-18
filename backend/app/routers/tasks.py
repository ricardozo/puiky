"""Endpoints HTTP del dominio de tareas."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.tasks import (
    ChecklistItemCreate,
    ChecklistItemUpdate,
    TaskCreate,
    TaskEstado,
    TaskOut,
    TaskProgress,
    TaskUpdate,
)
from app.services import tasks as service

router = APIRouter(prefix="/tasks", tags=["tareas"])


# --- Checklist (rutas literales, antes de /{task_id}) ---


@router.patch("/checklist/{item_id}", response_model=TaskOut)
def editar_item_checklist(
    item_id: uuid.UUID, data: ChecklistItemUpdate, db: Session = Depends(get_db)
) -> TaskOut:
    """Marca/desmarca o edita un ítem; recalcula el avance de la tarea."""
    tarea = service.update_checklist_item(db, item_id, data)
    if tarea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem no encontrado")
    return tarea


@router.delete("/checklist/{item_id}", response_model=TaskOut)
def eliminar_item_checklist(
    item_id: uuid.UUID, db: Session = Depends(get_db)
) -> TaskOut:
    tarea = service.delete_checklist_item(db, item_id)
    if tarea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem no encontrado")
    return tarea


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def crear_tarea(data: TaskCreate, db: Session = Depends(get_db)) -> TaskOut:
    try:
        return service.create_task(db, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("", response_model=list[TaskOut])
def listar_tareas(
    project_id: uuid.UUID | None = Query(default=None),
    estado: TaskEstado | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    """Lista tareas (por vencimiento), con filtros por proyecto, estado y texto."""
    valor_estado = estado.value if estado is not None else None
    return service.list_tasks(db, project_id, valor_estado, q)


# Rutas estáticas antes de /{task_id} para que no las capture el path param.
@router.get("/hoy", response_model=list[TaskOut])
def tareas_de_hoy(db: Session = Depends(get_db)) -> list[TaskOut]:
    """Tareas que vencen hoy o están vencidas y aún no terminadas."""
    return service.list_hoy(db)


@router.get("/pendientes", response_model=list[TaskOut])
def tareas_pendientes(db: Session = Depends(get_db)) -> list[TaskOut]:
    """Todas las tareas no terminadas."""
    return service.list_pendientes(db)


@router.get("/{task_id}", response_model=TaskOut)
def ver_tarea(task_id: uuid.UUID, db: Session = Depends(get_db)) -> TaskOut:
    tarea = service.get_task(db, task_id)
    if tarea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")
    return tarea


@router.put("/{task_id}", response_model=TaskOut)
def editar_tarea(
    task_id: uuid.UUID, data: TaskUpdate, db: Session = Depends(get_db)
) -> TaskOut:
    try:
        tarea = service.update_task(db, task_id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if tarea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")
    return tarea


@router.patch("/{task_id}/progress", response_model=TaskOut)
def marcar_avance(
    task_id: uuid.UUID, data: TaskProgress, db: Session = Depends(get_db)
) -> TaskOut:
    """Marca el porcentaje de avance (no cambia el estado)."""
    tarea = service.set_progress(db, task_id, data.avance_pct)
    if tarea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")
    return tarea


@router.post("/{task_id}/complete", response_model=TaskOut)
def completar_tarea(
    task_id: uuid.UUID, db: Session = Depends(get_db)
) -> TaskOut:
    """Marca la tarea como terminada (avance 100%)."""
    tarea = service.complete_task(db, task_id)
    if tarea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")
    return tarea


@router.post("/{task_id}/checklist", response_model=TaskOut)
def agregar_item_checklist(
    task_id: uuid.UUID, data: ChecklistItemCreate, db: Session = Depends(get_db)
) -> TaskOut:
    """Añade un ítem al checklist de la tarea."""
    tarea = service.add_checklist_item(db, task_id, data)
    if tarea is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")
    return tarea


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_tarea(task_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not service.delete_task(db, task_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")
