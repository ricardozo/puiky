"""Lógica de negocio del dominio de responsabilidades."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finances import Account, Category, Transaction
from app.models.responsibilities import Responsibility
from app.schemas.finances import TransactionCreate, TransactionTipo
from app.schemas.responsibilities import (
    ResponsibilityCreate,
    ResponsibilityPay,
    ResponsibilityUpdate,
)
from app.services import finances as fin
from app.services.recurrence import siguiente_vencimiento


def _categoria_otros(db: Session) -> Category:
    c = db.execute(
        select(Category).where(func.lower(Category.nombre) == "otros")
    ).scalar_one_or_none()
    if c is None:
        c = Category(nombre="Otros", activa=True)
        db.add(c)
        db.flush()
    return c


def _enriquecer(db: Session, resp: Responsibility) -> Responsibility:
    """Adjunta los nombres de cuenta/categoría para que el schema los muestre."""
    resp.cuenta = (  # type: ignore[attr-defined]
        db.get(Account, resp.account_id).nombre if resp.account_id else None
    )
    resp.categoria = (  # type: ignore[attr-defined]
        db.get(Category, resp.category_id).nombre if resp.category_id else None
    )
    return resp


def create_responsibility(
    db: Session, data: ResponsibilityCreate
) -> Responsibility:
    resp = Responsibility(
        nombre=data.nombre,
        recurrencia=data.recurrencia,
        proximo_venc=data.proximo_venc,
        monto=data.monto,
        account_id=data.account_id,
        category_id=data.category_id,
    )
    db.add(resp)
    db.commit()
    db.refresh(resp)
    return _enriquecer(db, resp)


def get_responsibility(
    db: Session, resp_id: uuid.UUID
) -> Responsibility | None:
    resp = db.get(Responsibility, resp_id)
    return _enriquecer(db, resp) if resp else None


def list_responsibilities(db: Session) -> list[Responsibility]:
    """Ordenadas por próximo vencimiento (lo más cercano primero)."""
    stmt = select(Responsibility).order_by(Responsibility.proximo_venc)
    return [_enriquecer(db, r) for r in db.execute(stmt).scalars().all()]


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
    return _enriquecer(db, resp)


def _avanzar(resp: Responsibility) -> None:
    """Recalcula el próximo vencimiento desde la fecha programada (no desde hoy):
    el arriendo vence el mismo día cada mes, se pague antes o después."""
    resp.proximo_venc = siguiente_vencimiento(resp.proximo_venc, resp.recurrencia)


def fulfill_responsibility(
    db: Session, resp_id: uuid.UUID
) -> Responsibility | None:
    """Marca cumplida (sin tocar finanzas): solo recalcula el vencimiento."""
    resp = db.get(Responsibility, resp_id)
    if resp is None:
        return None
    _avanzar(resp)
    db.commit()
    db.refresh(resp)
    return _enriquecer(db, resp)


def pay_responsibility(
    db: Session, resp_id: uuid.UUID, data: ResponsibilityPay | None = None
) -> tuple[Responsibility, Transaction | None] | None:
    """Registra el pago: si hay cuenta y monto, crea el gasto en finanzas
    (categoría indicada, o la guardada, o 'Otros'); luego avanza el vencimiento.
    Los datos de `data` (monto/cuenta/categoría) sobrescriben lo guardado."""
    resp = db.get(Responsibility, resp_id)
    if resp is None:
        return None
    data = data or ResponsibilityPay()
    account_id = data.account_id or resp.account_id
    monto = data.monto if data.monto is not None else resp.monto

    tx: Transaction | None = None
    if account_id is not None and monto is not None and monto > 0:
        category_id = data.category_id or resp.category_id or _categoria_otros(db).id
        tx = fin.create_transaction(
            db,
            TransactionCreate(
                tipo=TransactionTipo.gasto,
                monto=monto,
                account_id=account_id,
                category_id=category_id,
                nota=f"Pago: {resp.nombre}",
            ),
        )

    _avanzar(resp)
    db.commit()
    db.refresh(resp)
    return _enriquecer(db, resp), tx


def delete_responsibility(db: Session, resp_id: uuid.UUID) -> bool:
    resp = db.get(Responsibility, resp_id)
    if resp is None:
        return False
    db.delete(resp)
    db.commit()
    return True
