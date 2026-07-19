"""Endpoints HTTP de la lista de mercado."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.schemas.market import (
    ProductCreate,
    ProductOut,
    ProductUpdate,
    PurchaseCreate,
    PurchaseOut,
)
from app.services import market as service
from app.tenancy import get_tenant_db as get_db

router = APIRouter(prefix="/market", tags=["mercado"])


# --- Productos ---


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def crear_producto(data: ProductCreate, db: Session = Depends(get_db)) -> ProductOut:
    try:
        return service.create_product(db, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/products", response_model=list[ProductOut])
def listar_productos(
    solo_activos: bool = Query(default=False), db: Session = Depends(get_db)
) -> list[ProductOut]:
    return service.list_products(db, solo_activos)


@router.get("/por-comprar", response_model=list[ProductOut])
def listar_por_comprar(db: Session = Depends(get_db)) -> list[ProductOut]:
    """Productos activos que ya toca reponer (por su cadencia)."""
    return service.por_comprar(db)


@router.get("/products/{product_id}", response_model=ProductOut)
def ver_producto(product_id: uuid.UUID, db: Session = Depends(get_db)) -> ProductOut:
    p = service.get_product(db, product_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return p


@router.put("/products/{product_id}", response_model=ProductOut)
def editar_producto(
    product_id: uuid.UUID, data: ProductUpdate, db: Session = Depends(get_db)
) -> ProductOut:
    try:
        p = service.update_product(db, product_id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return p


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_producto(product_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not service.delete_product(db, product_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")


# --- Compras ---


@router.post(
    "/products/{product_id}/compras",
    response_model=PurchaseOut,
    status_code=status.HTTP_201_CREATED,
)
def registrar_compra(
    product_id: uuid.UUID, data: PurchaseCreate, db: Session = Depends(get_db)
) -> PurchaseOut:
    """Registra una compra del producto (reinicia su ciclo de recompra)."""
    compra = service.register_purchase(db, product_id, data)
    if compra is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return compra


@router.get("/products/{product_id}/compras", response_model=list[PurchaseOut])
def listar_compras(
    product_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[PurchaseOut]:
    return service.list_purchases(db, product_id)


@router.delete("/compras/{purchase_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_compra(purchase_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not service.delete_purchase(db, purchase_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compra no encontrada")
