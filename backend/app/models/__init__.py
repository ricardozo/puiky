"""Modelos ORM. Se importan aquí para que Base.metadata los conozca
(necesario para Alembic y para construir las relaciones)."""

from app.models.base import Base
from app.models.notes import Note, NoteLink

__all__ = ["Base", "Note", "NoteLink"]
