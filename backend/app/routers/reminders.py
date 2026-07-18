"""Endpoints HTTP del dominio de recordatorios."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.tenancy import get_tenant_db as get_db
from app.schemas.reminders import (
    ReminderCreate,
    ReminderOut,
    ReminderSnooze,
    ReminderUpdate,
)
from app.services import reminders as service

router = APIRouter(prefix="/reminders", tags=["recordatorios"])


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
def crear_recordatorio(
    data: ReminderCreate, db: Session = Depends(get_db)
) -> ReminderOut:
    try:
        return service.create_reminder(db, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("", response_model=list[ReminderOut])
def listar_recordatorios(
    resuelto: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ReminderOut]:
    return service.list_reminders(db, resuelto)


# Ruta estática antes de /{reminder_id}.
@router.get("/vencidos", response_model=list[ReminderOut])
def recordatorios_vencidos(db: Session = Depends(get_db)) -> list[ReminderOut]:
    """Sin resolver y cuyo disparo efectivo (o posposición) ya llegó."""
    return service.list_due(db)


@router.get("/{reminder_id}", response_model=ReminderOut)
def ver_recordatorio(
    reminder_id: uuid.UUID, db: Session = Depends(get_db)
) -> ReminderOut:
    reminder = service.get_reminder(db, reminder_id)
    if reminder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recordatorio no encontrado")
    return reminder


@router.put("/{reminder_id}", response_model=ReminderOut)
def editar_recordatorio(
    reminder_id: uuid.UUID, data: ReminderUpdate, db: Session = Depends(get_db)
) -> ReminderOut:
    reminder = service.update_reminder(db, reminder_id, data)
    if reminder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recordatorio no encontrado")
    return reminder


@router.post("/{reminder_id}/snooze", response_model=ReminderOut)
def posponer_recordatorio(
    reminder_id: uuid.UUID, data: ReminderSnooze, db: Session = Depends(get_db)
) -> ReminderOut:
    """Posponer ('recuérdame mañana')."""
    reminder = service.snooze_reminder(db, reminder_id, data.pospuesto_para)
    if reminder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recordatorio no encontrado")
    return reminder


@router.post("/{reminder_id}/notified", response_model=ReminderOut)
def registrar_aviso(
    reminder_id: uuid.UUID, db: Session = Depends(get_db)
) -> ReminderOut:
    """Incrementa el conteo de avisos (lo usará el scheduler para escalonar)."""
    reminder = service.mark_notified(db, reminder_id)
    if reminder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recordatorio no encontrado")
    return reminder


@router.post("/{reminder_id}/resolve", response_model=ReminderOut)
def resolver_recordatorio(
    reminder_id: uuid.UUID, db: Session = Depends(get_db)
) -> ReminderOut:
    """Marca resuelto (el asunto quedó atendido)."""
    reminder = service.resolve_reminder(db, reminder_id)
    if reminder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recordatorio no encontrado")
    return reminder


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_recordatorio(
    reminder_id: uuid.UUID, db: Session = Depends(get_db)
) -> None:
    if not service.delete_reminder(db, reminder_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recordatorio no encontrado")
