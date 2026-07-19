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
from sqlalchemy.orm import Mapped, mapped_column

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
