"""Modelos ORM. Se importan aquí para que las metadatas los conozcan
(necesario para Alembic y para construir las relaciones).

Dos metadatas (ver base.py):
- `ControlBase` → tablas de control en `public` (User, TelegramLink).
- `Base` → tablas de dominio, por schema de inquilino.
"""

from app.models.base import Base, ControlBase
from app.models.finances import Account, Budget, Category, Transaction
from app.models.market import MarketProduct, MarketPurchase
from app.models.notebooks import Notebook
from app.models.notes import Note, NoteLink
from app.models.portfolios import Portfolio
from app.models.projects import Project
from app.models.reminders import Reminder
from app.models.responsibilities import Responsibility
from app.models.tasks import ChecklistItem, Task
from app.models.users import TelegramLink, User

__all__ = [
    # Metadatas
    "Base",
    "ControlBase",
    # Control (public)
    "User",
    "TelegramLink",
    # Dominio (por inquilino)
    "Account",
    "Budget",
    "Category",
    "ChecklistItem",
    "MarketProduct",
    "MarketPurchase",
    "Note",
    "NoteLink",
    "Notebook",
    "Portfolio",
    "Project",
    "Reminder",
    "Responsibility",
    "Task",
    "Transaction",
]
