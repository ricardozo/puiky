"""Modelos del dominio de notas: Note y NoteLink."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import UUID, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.models.base import Base

# Dimensión del vector de embedding. Se lee del entorno para que columna,
# modelo y migración compartan una sola fuente. Debe coincidir con el valor
# fijado en la migración 0001 (768 para multilingual-e5-base).
EMBEDDING_DIM = get_settings().embedding_dim


class Note(Base):
    """El núcleo del sistema: la memoria (segundo cerebro)."""

    __tablename__ = "note"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    creada: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    links: Mapped[list["NoteLink"]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )


class NoteLink(Base):
    """Vínculo polimórfico: una nota apuntando a otra entidad.

    `entidad_tipo` es project / task / responsibility / account. Por ahora NO
    se valida la FK contra esas tablas (aún no existen) — deuda técnica a
    resolver cuando se creen los dominios correspondientes.
    """

    __tablename__ = "note_link"
    __table_args__ = (
        Index("ix_note_link_note_id", "note_id"),
        Index("ix_note_link_entidad", "entidad_tipo", "entidad_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("note.id", ondelete="CASCADE"), nullable=False
    )
    entidad_tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    entidad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    note: Mapped["Note"] = relationship(back_populates="links")
