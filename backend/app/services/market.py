"""Lógica de la lista de mercado.

Un producto está "por comprar" si está activo, tiene cadencia definida, y ya
pasó (o llegó) su cadencia desde la última compra —o si nunca se ha comprado.
Los derivados (última compra, por_comprar, días desde) se calculan y se adjuntan
al objeto para que el schema los serialice.
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.market import MarketProduct, MarketPurchase
from app.schemas.market import ProductCreate, ProductUpdate, PurchaseCreate


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
