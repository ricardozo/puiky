"""Modelo del dominio de recordatorios."""

import uuid
from datetime import datetime

from sqlalchemy import UUID, Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Reminder(Base):
    """Recordatorio atado (con origen) o suelto (sin origen).

    Los campos de conteo, posposición y resolución habilitan los avisos
    escalonados e insistentes que gestionará el scheduler (Fase 4)."""

    __tablename__ = "reminder"
    __table_args__ = (
        Index("ix_reminder_resuelto", "resuelto"),
        Index("ix_reminder_disparar_en", "disparar_en"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # task / responsibility / budget (opcional: null en recordatorios sueltos)
    origen_tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    origen_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    disparar_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    veces_avisado: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    # Posposición del USUARIO ("recuérdame mañana"): esconde el aviso de la web
    # y retrasa el bot hasta esa hora.
    pospuesto_para: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Cadencia de re-aviso del SCHEDULER (bot). Separado de pospuesto_para para
    # que la web siga mostrando lo vencido entre un aviso y el siguiente.
    proximo_aviso: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resuelto: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
