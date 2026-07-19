"""Modelos de la lista de mercado: MarketProduct y MarketPurchase.

Catálogo de productos recurrentes + historial de compras. El historial es la
base para los avisos de recompra (Fase A) y, más adelante, para descubrir los
ciclos de compra solos (Fase B).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    UUID,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MarketProduct(Base):
    """Producto que se compra con cierta regularidad."""

    __tablename__ = "market_product"
    __table_args__ = (Index("ix_market_product_category_id", "category_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    # unidad de medida: unidad / g / kg / ml / l
    unidad: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'unidad'")
    )
    # cantidad típica de la presentación (ej. 2.0 para "2 L"). Opcional.
    presentacion: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    # cadencia manual en días (cada cuánto se compra). Null = sin definir.
    cadencia_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # enlace opcional a una categoría de finanzas
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("category.id"), nullable=True
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    notas: Mapped[str | None] = mapped_column(String(300), nullable=True)
    creada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MarketPurchase(Base):
    """Una compra de un producto (histórico)."""

    __tablename__ = "market_purchase"
    __table_args__ = (
        Index("ix_market_purchase_product_id", "product_id"),
        Index("ix_market_purchase_fecha", "fecha"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_product.id", ondelete="CASCADE"),
        nullable=False,
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    # cuántas presentaciones/unidades se compraron
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, server_default=text("1")
    )
    precio: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    creada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ShoppingTrip(Base):
    """Una salida al supermercado (lista de compra en curso o cerrada)."""

    __tablename__ = "shopping_trip"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # abierta | cerrada
    estado: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'abierta'")
    )
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # cuenta y gasto de finanzas creados al cerrar (opcional)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id", ondelete="SET NULL"), nullable=True
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transaction.id", ondelete="SET NULL"),
        nullable=True,
    )
    creada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    cerrada_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    items: Mapped[list["TripItem"]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TripItem.orden",
    )


class TripItem(Base):
    """Un ítem de una compra: producto del catálogo o texto libre."""

    __tablename__ = "trip_item"
    __table_args__ = (Index("ix_trip_item_trip_id", "trip_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shopping_trip.id", ondelete="CASCADE"),
        nullable=False,
    )
    # enlace opcional al catálogo (para alimentar ciclos/precios al comprar)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("market_product.id", ondelete="SET NULL"),
        nullable=True,
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, server_default=text("1")
    )
    # "tamaño" de la presentación comprada (2 L, 500 g, …). Sin ñ en la columna.
    tamano: Mapped[str | None] = mapped_column(String(40), nullable=True)
    precio: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    comprado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    creada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    trip: Mapped["ShoppingTrip"] = relationship(back_populates="items")
