"""Lógica de negocio del dominio de recordatorios.

El disparo efectivo de un recordatorio es `pospuesto_para` si existe, si no
`disparar_en`. El envío proactivo lo hará el scheduler (Fase 4); aquí viven
los datos y las operaciones.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finances import Budget
from app.models.reminders import Reminder
from app.models.responsibilities import Responsibility
from app.models.tasks import Task
from app.schemas.reminders import ReminderCreate, ReminderUpdate

# origen_tipo -> modelo, para validar que el origen exista.
_MODELOS_ORIGEN = {
    "task": Task,
    "responsibility": Responsibility,
    "budget": Budget,
}


def create_reminder(db: Session, data: ReminderCreate) -> Reminder:
    if data.origen_tipo is not None:
        modelo = _MODELOS_ORIGEN[data.origen_tipo.value]
        if db.get(modelo, data.origen_id) is None:
            raise ValueError(f"El origen {data.origen_tipo.value} no existe")
    reminder = Reminder(
        texto=data.texto,
        disparar_en=data.disparar_en,
        origen_tipo=data.origen_tipo.value if data.origen_tipo else None,
        origen_id=data.origen_id,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def get_reminder(db: Session, reminder_id: uuid.UUID) -> Reminder | None:
    return db.get(Reminder, reminder_id)


def list_reminders(
    db: Session, resuelto: bool | None = None
) -> list[Reminder]:
    stmt = select(Reminder)
    if resuelto is not None:
        stmt = stmt.where(Reminder.resuelto.is_(resuelto))
    stmt = stmt.order_by(Reminder.disparar_en)
    return list(db.execute(stmt).scalars().all())


def list_due(db: Session) -> list[Reminder]:
    """Recordatorios sin resolver cuyo disparo efectivo ya llegó.

    Disparo efectivo = pospuesto_para si existe, si no disparar_en."""
    efectivo = func.coalesce(Reminder.pospuesto_para, Reminder.disparar_en)
    stmt = (
        select(Reminder)
        .where(Reminder.resuelto.is_(False), efectivo <= func.now())
        .order_by(efectivo)
    )
    return list(db.execute(stmt).scalars().all())


def update_reminder(
    db: Session, reminder_id: uuid.UUID, data: ReminderUpdate
) -> Reminder | None:
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(reminder, campo, valor)
    db.commit()
    db.refresh(reminder)
    return reminder


def snooze_reminder(
    db: Session, reminder_id: uuid.UUID, pospuesto_para
) -> Reminder | None:
    """Posponer: 'recuérdame mañana' sin perder el recordatorio."""
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        return None
    reminder.pospuesto_para = pospuesto_para
    db.commit()
    db.refresh(reminder)
    return reminder


def mark_notified(db: Session, reminder_id: uuid.UUID) -> Reminder | None:
    """Registra un aviso enviado (lo usará el scheduler para escalonar)."""
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        return None
    reminder.veces_avisado += 1
    db.commit()
    db.refresh(reminder)
    return reminder


def resolve_reminder(db: Session, reminder_id: uuid.UUID) -> Reminder | None:
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        return None
    reminder.resuelto = True
    db.commit()
    db.refresh(reminder)
    return reminder


def delete_reminder(db: Session, reminder_id: uuid.UUID) -> bool:
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        return False
    db.delete(reminder)
    db.commit()
    return True
