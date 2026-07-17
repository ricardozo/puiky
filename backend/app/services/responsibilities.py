"""Lógica de negocio del dominio de responsabilidades."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.responsibilities import Responsibility
from app.schemas.responsibilities import (
    ResponsibilityCreate,
    ResponsibilityUpdate,
)
from app.services.recurrence import siguiente_vencimiento


def create_responsibility(
    db: Session, data: ResponsibilityCreate
) -> Responsibility:
    resp = Responsibility(
        nombre=data.nombre,
        recurrencia=data.recurrencia,
        proximo_venc=data.proximo_venc,
        monto=data.monto,
    )
    db.add(resp)
    db.commit()
    db.refresh(resp)
    return resp


def get_responsibility(
    db: Session, resp_id: uuid.UUID
) -> Responsibility | None:
    return db.get(Responsibility, resp_id)


def list_responsibilities(db: Session) -> list[Responsibility]:
    """Ordenadas por próximo vencimiento (lo más cercano primero)."""
    stmt = select(Responsibility).order_by(Responsibility.proximo_venc)
    return list(db.execute(stmt).scalars().all())


def update_responsibility(
    db: Session, resp_id: uuid.UUID, data: ResponsibilityUpdate
) -> Responsibility | None:
    resp = db.get(Responsibility, resp_id)
    if resp is None:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(resp, campo, valor)
    db.commit()
    db.refresh(resp)
    return resp


def fulfill_responsibility(
    db: Session, resp_id: uuid.UUID
) -> Responsibility | None:
    """Marca cumplida: recalcula el próximo vencimiento según la recurrencia.

    Se recalcula desde la fecha de vencimiento programada (no desde hoy), como
    es habitual en compromisos periódicos (el arriendo vence el mismo día cada
    mes, se pague antes o después)."""
    resp = db.get(Responsibility, resp_id)
    if resp is None:
        return None
    resp.proximo_venc = siguiente_vencimiento(resp.proximo_venc, resp.recurrencia)
    db.commit()
    db.refresh(resp)
    return resp


def delete_responsibility(db: Session, resp_id: uuid.UUID) -> bool:
    resp = db.get(Responsibility, resp_id)
    if resp is None:
        return False
    db.delete(resp)
    db.commit()
    return True
