"""Modelo del dominio de proyectos."""

import uuid

from sqlalchemy import UUID, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Project(Base):
    """Agrupa tareas y puede ser referido por notas (vía NOTE_LINK)."""

    __tablename__ = "project"
    __table_args__ = (Index("ix_project_portfolio_id", "portfolio_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # activo / pausado / terminado (archivar = terminado)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'activo'")
    )
    # Portafolio al que pertenece (opcional: null = sin portafolio).
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolio.id", ondelete="SET NULL"),
        nullable=True,
    )

    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        back_populates="project", order_by="Task.fecha_limite"
    )
