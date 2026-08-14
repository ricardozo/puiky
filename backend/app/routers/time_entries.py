"""Endpoints HTTP del registro de tiempo."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.schemas.time_entries import TimeEntryOut, TimeEntryStart, TimeEntryUpdate
from app.services import time_entries as service
from app.tenancy import get_tenant_db as get_db

router = APIRouter(prefix="/time", tags=["tiempo"])


@router.post("/start", response_model=TimeEntryOut, status_code=status.HTTP_201_CREATED)
def iniciar_sesion(data: TimeEntryStart, db: Session = Depends(get_db)) -> TimeEntryOut:
    """Arranca una sesión sobre la tarea; cierra la que estuviera corriendo."""
    try:
        return service.start_entry(db, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post("/stop", response_model=TimeEntryOut)
def parar_sesion(db: Session = Depends(get_db)) -> TimeEntryOut:
    entry = service.stop_entry(db)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay sesión corriendo")
    return entry


@router.get("/actual", response_model=TimeEntryOut | None)
def sesion_actual(db: Session = Depends(get_db)) -> TimeEntryOut | None:
    """La sesión corriendo, o null."""
    return service.current_entry(db)


@router.get("", response_model=list[TimeEntryOut])
def listar_sesiones(
    dia: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[TimeEntryOut]:
    """Sesiones del día indicado (hoy por defecto)."""
    return service.list_entries(db, dia)


@router.put("/{entry_id}", response_model=TimeEntryOut)
def editar_sesion(
    entry_id: uuid.UUID, data: TimeEntryUpdate, db: Session = Depends(get_db)
) -> TimeEntryOut:
    try:
        entry = service.update_entry(db, entry_id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada")
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_sesion(entry_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not service.delete_entry(db, entry_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesión no encontrada")
