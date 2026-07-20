"""Endpoints HTTP del dominio de responsabilidades."""

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.finances import Account
from app.tenancy import get_tenant_db as get_db
from app.schemas.responsibilities import (
    ResponsibilityCreate,
    ResponsibilityOut,
    ResponsibilityPay,
    ResponsibilityPayResult,
    ResponsibilityUpdate,
)
from app.services import responsibilities as service

router = APIRouter(prefix="/responsibilities", tags=["responsabilidades"])


@router.post(
    "", response_model=ResponsibilityOut, status_code=status.HTTP_201_CREATED
)
def crear_responsabilidad(
    data: ResponsibilityCreate, db: Session = Depends(get_db)
) -> ResponsibilityOut:
    return service.create_responsibility(db, data)


@router.get("", response_model=list[ResponsibilityOut])
def listar_responsabilidades(
    db: Session = Depends(get_db),
) -> list[ResponsibilityOut]:
    """Próximos vencimientos (lo más cercano primero)."""
    return service.list_responsibilities(db)


@router.get("/{resp_id}", response_model=ResponsibilityOut)
def ver_responsabilidad(
    resp_id: uuid.UUID, db: Session = Depends(get_db)
) -> ResponsibilityOut:
    resp = service.get_responsibility(db, resp_id)
    if resp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Responsabilidad no encontrada")
    return resp


@router.put("/{resp_id}", response_model=ResponsibilityOut)
def editar_responsabilidad(
    resp_id: uuid.UUID,
    data: ResponsibilityUpdate,
    db: Session = Depends(get_db),
) -> ResponsibilityOut:
    resp = service.update_responsibility(db, resp_id, data)
    if resp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Responsabilidad no encontrada")
    return resp


@router.post("/{resp_id}/fulfill", response_model=ResponsibilityOut)
def cumplir_responsabilidad(
    resp_id: uuid.UUID, db: Session = Depends(get_db)
) -> ResponsibilityOut:
    """Marca cumplida y recalcula el próximo vencimiento (sin tocar finanzas)."""
    resp = service.fulfill_responsibility(db, resp_id)
    if resp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Responsabilidad no encontrada")
    return resp


@router.post("/{resp_id}/pay", response_model=ResponsibilityPayResult)
def registrar_pago(
    resp_id: uuid.UUID,
    data: ResponsibilityPay = Body(default_factory=ResponsibilityPay),
    db: Session = Depends(get_db),
) -> ResponsibilityPayResult:
    """Registra el pago: crea el gasto en finanzas (si hay cuenta y monto) y
    avanza el próximo vencimiento."""
    try:
        result = service.pay_responsibility(db, resp_id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Responsabilidad no encontrada")
    resp, tx = result
    cuenta = db.get(Account, tx.account_id) if tx else None
    return ResponsibilityPayResult(
        responsabilidad=ResponsibilityOut.model_validate(resp),
        gasto_creado=tx is not None,
        monto=tx.monto if tx else None,
        cuenta=cuenta.nombre if cuenta else None,
        saldo_cuenta=cuenta.saldo if cuenta else None,
    )


@router.delete("/{resp_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_responsabilidad(
    resp_id: uuid.UUID, db: Session = Depends(get_db)
) -> None:
    if not service.delete_responsibility(db, resp_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Responsabilidad no encontrada")
