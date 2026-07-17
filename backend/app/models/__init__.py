"""Modelos ORM. Se importan aquí para que Base.metadata los conozca
(necesario para Alembic y para construir las relaciones)."""

from app.models.base import Base
from app.models.notes import Note, NoteLink
from app.models.projects import Project
from app.models.tasks import Task

__all__ = ["Base", "Note", "NoteLink", "Project", "Task"]
