"""Lógica de negocio del dominio de recordatorios.

El disparo efectivo de un recordatorio es `pospuesto_para` si existe, si no
`disparar_en`. El envío proactivo lo hará el scheduler (Fase 4); aquí viven
los datos y las operaciones.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finances import Budget
from app.models.reminders import Reminder
from app.models.responsibilities import Responsibility
from app.models.tasks import Task
from app.schemas.reminders import ReminderCreate, ReminderUpdate
from app.services.recurrence import siguiente_vencimiento

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
        recurrencia=data.recurrencia,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


_ETIQUETAS = {"task": "La tarea", "responsibility": "La responsabilidad"}


def texto_vencimiento(etiqueta: str, nombre: str, venc: date, hoy: date) -> str:
    """Frase relativa a HOY («vence mañana», «venció hace 3 días»). Se
    recalcula cada vez: un texto fijado al generar el aviso queda desfasado."""
    dias = (venc - hoy).days
    if dias == 0:
        cuando = "vence hoy"
    elif dias == 1:
        cuando = "vence mañana"
    elif dias > 1:
        cuando = f"vence en {dias} días"
    elif dias == -1:
        cuando = "venció ayer"
    else:
        cuando = f"venció hace {-dias} días"
    return f"⏰ {etiqueta} «{nombre}» {cuando}."


def vivificar(db: Session, reminders: list[Reminder]) -> list[Reminder]:
    """Actualiza el texto de los avisos atados a una tarea/responsabilidad
    según su vencimiento ACTUAL y adjunta `vence` (la fecha real), para que
    texto y color digan lo mismo. Los demás se dejan igual."""
    from app.timeutils import now_local

    hoy = now_local().date()
    for r in reminders:
        r.vence = None  # type: ignore[attr-defined]
        if r.origen_tipo not in _ETIQUETAS or r.origen_id is None:
            continue
        origen = db.get(_MODELOS_ORIGEN[r.origen_tipo], r.origen_id)
        if origen is None:
            continue
        if r.origen_tipo == "task":
            nombre, venc = origen.titulo, origen.fecha_limite
        else:
            nombre, venc = origen.nombre, origen.proximo_venc
        if venc is None:
            continue
        r.vence = venc  # type: ignore[attr-defined]
        texto = texto_vencimiento(_ETIQUETAS[r.origen_tipo], nombre, venc, hoy)
        if r.texto != texto:
            r.texto = texto
    return reminders


def get_reminder(db: Session, reminder_id: uuid.UUID) -> Reminder | None:
    r = db.get(Reminder, reminder_id)
    return vivificar(db, [r])[0] if r else None


def list_reminders(
    db: Session, resuelto: bool | None = None
) -> list[Reminder]:
    stmt = select(Reminder)
    if resuelto is not None:
        stmt = stmt.where(Reminder.resuelto.is_(resuelto))
    stmt = stmt.order_by(Reminder.disparar_en)
    return vivificar(db, list(db.execute(stmt).scalars().all()))


def list_due(db: Session) -> list[Reminder]:
    """Recordatorios sin resolver cuyo disparo efectivo ya llegó.

    Disparo efectivo = pospuesto_para si existe, si no disparar_en."""
    efectivo = func.coalesce(Reminder.pospuesto_para, Reminder.disparar_en)
    stmt = (
        select(Reminder)
        .where(Reminder.resuelto.is_(False), efectivo <= func.now())
        .order_by(efectivo)
    )
    return vivificar(db, list(db.execute(stmt).scalars().all()))


def update_reminder(
    db: Session, reminder_id: uuid.UUID, data: ReminderUpdate
) -> Reminder | None:
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        return None
    cambios = data.model_dump(exclude_unset=True)
    for campo, valor in cambios.items():
        setattr(reminder, campo, valor)
    if "disparar_en" in cambios:
        # Fecha nueva: parte de cero (sin posposición ni avisos acumulados).
        reminder.pospuesto_para = None
        reminder.veces_avisado = 0
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
    """Resuelve el recordatorio. Si es recurrente, en vez de cerrarlo lo reprograma
    para el siguiente periodo (y limpia el estado de aviso), para que reaparezca."""
    reminder = db.get(Reminder, reminder_id)
    if reminder is None:
        return None
    if reminder.recurrencia:
        base = reminder.pospuesto_para or reminder.disparar_en
        siguiente = siguiente_vencimiento(base.date(), reminder.recurrencia)
        reminder.disparar_en = datetime.combine(
            siguiente, reminder.disparar_en.timetz()
        )
        reminder.pospuesto_para = None
        reminder.proximo_aviso = None
        reminder.veces_avisado = 0
        reminder.resuelto = False
    else:
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
