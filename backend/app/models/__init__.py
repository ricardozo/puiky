"""Modelos ORM. Se importan aquí para que Base.metadata los conozca
(necesario para Alembic y para construir las relaciones)."""

from app.models.base import Base
from app.models.finances import Account, Budget, Category, Transaction
from app.models.notes import Note, NoteLink
from app.models.projects import Project
from app.models.reminders import Reminder
from app.models.responsibilities import Responsibility
from app.models.tasks import Task
from app.models.users import User

__all__ = [
    "Base",
    "Account",
    "Budget",
    "Category",
    "Note",
    "NoteLink",
    "Project",
    "Reminder",
    "Responsibility",
    "Task",
    "Transaction",
    "User",
]
