"""Modelo del dominio de responsabilidades (compromisos recurrentes)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import UUID, Date, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Responsibility(Base):
    """Compromiso que se repite (arriendo, renovaciones). Al cumplirse, su
    `proximo_venc` se recalcula según `recurrencia`."""

    __tablename__ = "responsibility"
    __table_args__ = (Index("ix_responsibility_proximo_venc", "proximo_venc"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    # diaria / semanal / mensual / trimestral / anual / cada_N_dias
    recurrencia: Mapped[str] = mapped_column(String(30), nullable=False)
    proximo_venc: Mapped[date] = mapped_column(Date, nullable=False)
    monto: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
