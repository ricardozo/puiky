"""Modelo del registro de tiempo: sesiones de trabajo sobre una tarea."""

import uuid
from datetime import datetime

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TimeEntry(Base):
    """Sesión de tiempo dedicada a una tarea (de un proyecto o de «Vida»).

    `fin` en NULL = sesión corriendo. Solo debe haber una corriendo a la vez;
    el servicio cierra la anterior al iniciar una nueva. Inicio y fin son
    editables después (p. ej. si el usuario olvidó parar)."""

    __tablename__ = "time_entry"
    __table_args__ = (
        Index("ix_time_entry_task_id", "task_id"),
        Index("ix_time_entry_inicio", "inicio"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
    )
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fin: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    nota: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Pomodoro: a los cuántos minutos avisar por Telegram (NULL = sin aviso),
    # y si el aviso de esta sesión ya se envió.
    aviso_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avisado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
