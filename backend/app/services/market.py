"""Lógica de la lista de mercado.

Un producto está "por comprar" si está activo, tiene cadencia definida, y ya
pasó (o llegó) su cadencia desde la última compra —o si nunca se ha comprado.
Los derivados (última compra, por_comprar, días desde) se calculan y se adjuntan
al objeto para que el schema los serialice.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.finances import Category
from app.models.market import MarketProduct, MarketPurchase, ShoppingTrip, TripItem
from app.models.reminders import Reminder
from app.schemas.finances import TransactionCreate, TransactionTipo
from app.schemas.market import (
    CerrarCompra,
    ProductCreate,
    ProductUpdate,
    PurchaseCreate,
    TripItemCreate,
    TripItemUpdate,
)
from app.services import finances as fin
from app.timeutils import now_local


def _ultimas_compras(db: Session) -> dict[uuid.UUID, date]:
    filas = db.execute(
        select(MarketPurchase.product_id, func.max(MarketPurchase.fecha)).group_by(
            MarketPurchase.product_id
        )
    ).all()
    return {pid: f for pid, f in filas}


def _enriquecer(p: MarketProduct, ultima: date | None, hoy: date) -> MarketProduct:
    p.ultima_compra = ultima  # type: ignore[attr-defined]
    p.dias_desde = (hoy - ultima).days if ultima else None  # type: ignore[attr-defined]
    if not p.activo or p.cadencia_dias is None:
        por_comprar = False
    elif ultima is None:
        por_comprar = True  # definido pero sin comprar aún
    else:
        por_comprar = (hoy - ultima).days >= p.cadencia_dias
    p.por_comprar = por_comprar  # type: ignore[attr-defined]
    return p


# --- Productos ---


def create_product(db: Session, data: ProductCreate) -> MarketProduct:
    existe = db.execute(
        select(MarketProduct).where(
            func.lower(MarketProduct.nombre) == data.nombre.lower()
        )
    ).scalar_one_or_none()
    if existe is not None:
        raise ValueError("Ya existe un producto con ese nombre")
    if data.category_id is not None:
        from app.models.finances import Category

        if db.get(Category, data.category_id) is None:
            raise ValueError("La categoría no existe")
    p = MarketProduct(
        nombre=data.nombre,
        unidad=data.unidad,
        presentacion=data.presentacion,
        cadencia_dias=data.cadencia_dias,
        category_id=data.category_id,
        notas=data.notas,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _enriquecer(p, None, date.today())


def get_product(db: Session, product_id: uuid.UUID) -> MarketProduct | None:
    p = db.get(MarketProduct, product_id)
    if p is None:
        return None
    ultimas = _ultimas_compras(db)
    return _enriquecer(p, ultimas.get(p.id), date.today())


def list_products(db: Session, solo_activos: bool = False) -> list[MarketProduct]:
    stmt = select(MarketProduct)
    if solo_activos:
        stmt = stmt.where(MarketProduct.activo.is_(True))
    prods = list(db.execute(stmt.order_by(MarketProduct.nombre)).scalars().all())
    ultimas = _ultimas_compras(db)
    hoy = date.today()
    return [_enriquecer(p, ultimas.get(p.id), hoy) for p in prods]


def por_comprar(db: Session) -> list[MarketProduct]:
    """Productos activos que ya toca reponer, ordenados por urgencia."""
    pendientes = [p for p in list_products(db, solo_activos=True) if p.por_comprar]  # type: ignore[attr-defined]
    # más atrasados primero (los sin fecha, al principio)
    return sorted(
        pendientes,
        key=lambda p: (p.dias_desde if p.dias_desde is not None else 10**9),  # type: ignore[attr-defined]
        reverse=True,
    )


def update_product(
    db: Session, product_id: uuid.UUID, data: ProductUpdate
) -> MarketProduct | None:
    p = db.get(MarketProduct, product_id)
    if p is None:
        return None
    cambios = data.model_dump(exclude_unset=True)
    if "nombre" in cambios:
        otro = db.execute(
            select(MarketProduct).where(
                func.lower(MarketProduct.nombre) == cambios["nombre"].lower(),
                MarketProduct.id != product_id,
            )
        ).scalar_one_or_none()
        if otro is not None:
            raise ValueError("Ya existe un producto con ese nombre")
    for campo, valor in cambios.items():
        setattr(p, campo, valor)
    db.commit()
    db.refresh(p)
    ultimas = _ultimas_compras(db)
    return _enriquecer(p, ultimas.get(p.id), date.today())


def delete_product(db: Session, product_id: uuid.UUID) -> bool:
    p = db.get(MarketProduct, product_id)
    if p is None:
        return False
    db.delete(p)  # las compras caen por ON DELETE CASCADE
    db.commit()
    return True


# --- Compras ---


def register_purchase(
    db: Session, product_id: uuid.UUID, data: PurchaseCreate
) -> MarketPurchase | None:
    if db.get(MarketProduct, product_id) is None:
        return None
    compra = MarketPurchase(
        product_id=product_id,
        fecha=data.fecha or date.today(),
        cantidad=data.cantidad,
        precio=data.precio,
    )
    db.add(compra)
    # cierra el aviso de recompra pendiente de este producto (si lo hay)
    db.execute(
        update(Reminder)
        .where(
            Reminder.origen_tipo == "market",
            Reminder.origen_id == product_id,
            Reminder.resuelto.is_(False),
        )
        .values(resuelto=True)
    )
    db.commit()
    db.refresh(compra)
    return compra


def list_purchases(
    db: Session, product_id: uuid.UUID
) -> list[MarketPurchase]:
    return list(
        db.execute(
            select(MarketPurchase)
            .where(MarketPurchase.product_id == product_id)
            .order_by(MarketPurchase.fecha.desc())
        )
        .scalars()
        .all()
    )


def delete_purchase(db: Session, purchase_id: uuid.UUID) -> bool:
    compra = db.get(MarketPurchase, purchase_id)
    if compra is None:
        return False
    db.delete(compra)
    db.commit()
    return True


# --- Modo compra (una salida al súper) ---


def get_open_trip(db: Session) -> ShoppingTrip | None:
    return (
        db.execute(
            select(ShoppingTrip)
            .where(ShoppingTrip.estado == "abierta")
            .order_by(ShoppingTrip.creada.desc())
        )
        .scalars()
        .first()
    )


def start_trip(db: Session) -> ShoppingTrip:
    """Devuelve la compra abierta o crea una nueva (una abierta a la vez)."""
    t = get_open_trip(db)
    if t is not None:
        return t
    t = ShoppingTrip()
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def get_trip(db: Session, trip_id: uuid.UUID) -> ShoppingTrip | None:
    return db.get(ShoppingTrip, trip_id)


def _next_orden(db: Session, trip_id: uuid.UUID) -> int:
    m = db.execute(
        select(func.max(TripItem.orden)).where(TripItem.trip_id == trip_id)
    ).scalar()
    return (m or 0) + 1


def add_item(db: Session, trip_id: uuid.UUID, data: TripItemCreate) -> TripItem | None:
    trip = db.get(ShoppingTrip, trip_id)
    if trip is None or trip.estado != "abierta":
        return None
    product_id = data.product_id
    if product_id is None:  # enlaza por nombre exacto con el catálogo, si existe
        prod = db.execute(
            select(MarketProduct).where(
                func.lower(MarketProduct.nombre) == data.nombre.lower()
            )
        ).scalar_one_or_none()
        if prod is not None:
            product_id = prod.id
    item = TripItem(
        trip_id=trip_id,
        product_id=product_id,
        nombre=data.nombre,
        cantidad=data.cantidad,
        tamano=data.tamano,
        precio=data.precio,
        comprado=data.comprado,
        orden=_next_orden(db, trip_id),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def add_suggestions(db: Session, trip_id: uuid.UUID) -> int:
    """Agrega a la lista los productos que toca reponer y que no estén ya."""
    trip = db.get(ShoppingTrip, trip_id)
    if trip is None or trip.estado != "abierta":
        return 0
    ya = {i.product_id for i in trip.items if i.product_id is not None}
    creados = 0
    for p in por_comprar(db):
        if p.id in ya:
            continue
        db.add(
            TripItem(
                trip_id=trip_id,
                product_id=p.id,
                nombre=p.nombre,
                orden=_next_orden(db, trip_id),
            )
        )
        creados += 1
    if creados:
        db.commit()
    return creados


def update_item(
    db: Session, item_id: uuid.UUID, data: TripItemUpdate
) -> TripItem | None:
    item = db.get(TripItem, item_id)
    if item is None:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(item, campo, valor)
    db.commit()
    db.refresh(item)
    return item


def remove_item(db: Session, item_id: uuid.UUID) -> bool:
    item = db.get(TripItem, item_id)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def cancel_trip(db: Session, trip_id: uuid.UUID) -> bool:
    """Descarta una compra abierta (borra la lista, sin registrar nada)."""
    trip = db.get(ShoppingTrip, trip_id)
    if trip is None or trip.estado != "abierta":
        return False
    db.delete(trip)  # los ítems caen por ON DELETE CASCADE
    db.commit()
    return True


def _find_or_create_category(db: Session, nombre: str) -> Category:
    c = db.execute(
        select(Category).where(func.lower(Category.nombre) == nombre.lower())
    ).scalar_one_or_none()
    if c is None:
        c = Category(nombre=nombre, activa=True)
        db.add(c)
        db.flush()
    return c


def cerrar_trip(
    db: Session, trip_id: uuid.UUID, data: CerrarCompra
) -> ShoppingTrip | None:
    trip = db.get(ShoppingTrip, trip_id)
    if trip is None:
        return None
    if trip.estado == "cerrada":
        return trip  # idempotente

    comprados = [i for i in trip.items if i.comprado]
    total = sum((i.precio for i in comprados if i.precio is not None), Decimal("0"))

    # Gasto en finanzas (opcional, si hay cuenta y total > 0)
    if data.account_id is not None and total > 0:
        cat = _find_or_create_category(db, data.categoria or "Mercado")
        tx = fin.create_transaction(
            db,
            TransactionCreate(
                tipo=TransactionTipo.gasto,
                monto=total,
                account_id=data.account_id,
                category_id=cat.id,
                nota="Compra de mercado",
            ),
        )
        trip.transaction_id = tx.id
        trip.account_id = data.account_id

    # Registra en el catálogo las compras (alimenta ciclos/precios, cierra avisos)
    for i in comprados:
        if i.product_id is not None:
            register_purchase(
                db, i.product_id, PurchaseCreate(cantidad=i.cantidad, precio=i.precio)
            )

    trip.total = total
    trip.estado = "cerrada"
    trip.cerrada_en = now_local()
    db.commit()
    db.refresh(trip)
    return trip
