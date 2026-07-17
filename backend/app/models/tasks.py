"""Modelo del dominio de tareas."""

import uuid
from datetime import date

from sqlalchemy import UUID, Date, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Task(Base):
    """Los cuatro `estado` son las columnas del tablero Kanban del proyecto."""

    __tablename__ = "task"
    __table_args__ = (
        Index("ix_task_project_id", "project_id"),
        Index("ix_task_estado", "estado"),
        Index("ix_task_fecha_limite", "fecha_limite"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="SET NULL"),
        nullable=True,
    )
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    # planeada / en_ejecucion / en_pausa / terminada
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'planeada'")
    )
    avance_pct: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)

    project: Mapped["Project | None"] = relationship(  # noqa: F821
        back_populates="tasks"
    )
