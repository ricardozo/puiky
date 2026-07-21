"""Modelo del dominio de tareas y sus ítems de checklist."""

import uuid
from datetime import date

from sqlalchemy import (
    UUID,
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
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
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    # planeada / en_ejecucion / en_pausa / terminada
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'planeada'")
    )
    # Avance %. Manual si no hay checklist; calculado del checklist si lo hay.
    avance_pct: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    # Fechas. `fecha_limite` es el FIN PLANEADO (deadline; lo usa el scheduler).
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_inicio_plan: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_inicio_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_fin_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Si está definida, al completar la tarea se reinicia y su fecha_limite avanza
    # al siguiente periodo. Gramática: diaria|semanal|mensual|...|cada_N_dias.
    recurrencia: Mapped[str | None] = mapped_column(String(30), nullable=True)

    project: Mapped["Project | None"] = relationship(  # noqa: F821
        back_populates="tasks"
    )
    checklist: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ChecklistItem.orden",
    )

    @property
    def proyecto(self) -> str | None:
        """Nombre del proyecto (para exponerlo en los listados)."""
        return self.project.nombre if self.project else None


class ChecklistItem(Base):
    """Ítem marcable de una tarea. Su proporción marcada da el % de avance."""

    __tablename__ = "checklist_item"
    __table_args__ = (Index("ix_checklist_item_task_id", "task_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task.id", ondelete="CASCADE"), nullable=False
    )
    texto: Mapped[str] = mapped_column(String(300), nullable=False)
    hecho: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    orden: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    task: Mapped["Task"] = relationship(back_populates="checklist")
