"""dominio baseline: todas las tablas de dominio en el schema del inquilino

Cadena de DOMINIO (branch 'domain'). Se aplica por cada schema de inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

Consolida el esquema histórico (0001–0011, archivadas) en un baseline único que
crea las tablas directamente desde la metadata de dominio (exacto a los modelos,
incluyendo pgvector e índices). Las tablas se crean en el `search_path` del
inquilino (lo fija env.py). La extensión `vector` la provee la cadena de control.

Revision ID: domain_0001
Revises:
Create Date: 2026-07-18
"""

from collections.abc import Sequence

from alembic import op

from app.models import Base

revision: str = "domain_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = ("domain",)
depends_on: str | None = None

# Baseline CONGELADO: exactamente las tablas de dominio que existían al crear el
# baseline. Se lista explícito (no toda la metadata viva) para que agregar
# modelos nuevos vaya en migraciones incrementales (domain_0002, …) y no aquí.
_BASELINE_TABLES = (
    "notebook",
    "note",
    "note_link",
    "portfolio",
    "project",
    "task",
    "checklist_item",
    "account",
    "category",
    "transaction",
    "budget",
    "reminder",
    "responsibility",
)


def upgrade() -> None:
    md = Base.metadata
    md.create_all(bind=op.get_bind(), tables=[md.tables[t] for t in _BASELINE_TABLES])


def downgrade() -> None:
    md = Base.metadata
    md.drop_all(bind=op.get_bind(), tables=[md.tables[t] for t in _BASELINE_TABLES])
