"""Modelos del dominio de finanzas: Account, Category, Transaction, Budget."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import UUID, Boolean, Date, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Account(Base):
    """Cuenta con saldo. La de ahorros es una cuenta normal más."""

    __tablename__ = "account"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    # efectivo / banco / ahorros / … (sugeridos, extensible)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    saldo: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, server_default=text("0")
    )


class Category(Base):
    """Categoría de movimientos. Fijas pero extensibles; se desactivan, no se
    borran (para no romper el histórico de movimientos)."""

    __tablename__ = "category"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nombre: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    activa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )


class Transaction(Base):
    """Movimiento: gasto, ingreso o transferencia interna.

    `tipo=transferencia` mueve saldo de `account_id` a `cuenta_destino_id` y se
    excluye de los reportes de gasto (no es gasto real)."""

    __tablename__ = "transaction"
    __table_args__ = (
        Index("ix_transaction_account_id", "account_id"),
        Index("ix_transaction_category_id", "category_id"),
        Index("ix_transaction_fecha", "fecha"),
        Index("ix_transaction_tipo", "tipo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # gasto / ingreso / transferencia
    tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    cuenta_destino_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account.id"), nullable=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("category.id"), nullable=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    nota: Mapped[str | None] = mapped_column(String(500), nullable=True)


class Budget(Base):
    """Tope de gasto. Con `category_id` es por categoría; sin él, es el
    presupuesto global del mes."""

    __tablename__ = "budget"
    __table_args__ = (Index("ix_budget_category_id", "category_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("category.id"), nullable=True
    )
    tope: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    periodo: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'mensual'")
    )
