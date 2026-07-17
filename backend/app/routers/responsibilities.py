"""Endpoints HTTP del dominio de responsabilidades."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.responsibilities import (
    ResponsibilityCreate,
    ResponsibilityOut,
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
    """Marca cumplida y recalcula el próximo vencimiento."""
    resp = service.fulfill_responsibility(db, resp_id)
    if resp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Responsabilidad no encontrada")
    return resp


@router.delete("/{resp_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_responsabilidad(
    resp_id: uuid.UUID, db: Session = Depends(get_db)
) -> None:
    if not service.delete_responsibility(db, resp_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Responsabilidad no encontrada")
