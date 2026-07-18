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


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
