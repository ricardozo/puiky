"""Endpoints HTTP de la lista de mercado."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.schemas.market import (
    CerrarCompra,
    ProductCreate,
    ProductOut,
    ProductUpdate,
    PurchaseCreate,
    PurchaseOut,
    TripItemCreate,
    TripItemOut,
    TripItemUpdate,
    TripOut,
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


# --- Modo compra ---


@router.post("/trip", response_model=TripOut)
def iniciar_compra(db: Session = Depends(get_db)) -> TripOut:
    """Inicia (o retoma) la compra en curso."""
    return service.start_trip(db)


@router.get("/trip", response_model=TripOut | None)
def compra_en_curso(db: Session = Depends(get_db)) -> TripOut | None:
    """La compra abierta, o null si no hay ninguna."""
    return service.get_open_trip(db)


@router.get("/trip/{trip_id}", response_model=TripOut)
def ver_compra(trip_id: uuid.UUID, db: Session = Depends(get_db)) -> TripOut:
    trip = service.get_trip(db, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compra no encontrada")
    return trip


@router.delete("/trip/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_compra(trip_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Descarta una compra abierta (sin registrar nada)."""
    if not service.cancel_trip(db, trip_id):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Compra no encontrada o ya cerrada"
        )


@router.post(
    "/trip/{trip_id}/items", response_model=TripItemOut, status_code=status.HTTP_201_CREATED
)
def agregar_item(
    trip_id: uuid.UUID, data: TripItemCreate, db: Session = Depends(get_db)
) -> TripItemOut:
    item = service.add_item(db, trip_id, data)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compra no encontrada o cerrada")
    return item


@router.post("/trip/{trip_id}/sugerir", response_model=TripOut)
def sugerir_items(trip_id: uuid.UUID, db: Session = Depends(get_db)) -> TripOut:
    """Agrega a la lista los productos que toca reponer."""
    service.add_suggestions(db, trip_id)
    trip = service.get_trip(db, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compra no encontrada")
    return trip


@router.put("/trip/items/{item_id}", response_model=TripItemOut)
def editar_item(
    item_id: uuid.UUID, data: TripItemUpdate, db: Session = Depends(get_db)
) -> TripItemOut:
    """Edita un ítem: marcar comprado, precio, tamaño, cantidad, nombre."""
    item = service.update_item(db, item_id, data)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem no encontrado")
    return item


@router.delete("/trip/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def quitar_item(item_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not service.remove_item(db, item_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem no encontrado")


@router.post("/trip/{trip_id}/cerrar", response_model=TripOut)
def cerrar_compra(
    trip_id: uuid.UUID, data: CerrarCompra, db: Session = Depends(get_db)
) -> TripOut:
    """Cierra la compra: calcula el total, registra las compras del catálogo y
    (si se indica cuenta) crea el gasto en finanzas."""
    try:
        trip = service.cerrar_trip(db, trip_id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compra no encontrada")
    return trip
