"""dominio: recurrencia en tareas y recordatorios

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

Revision ID: domain_0009
Revises: domain_0008
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "domain_0009"
down_revision: str | None = "domain_0008"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("task", sa.Column("recurrencia", sa.String(length=30), nullable=True))
    op.add_column(
        "reminder", sa.Column("recurrencia", sa.String(length=30), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("reminder", "recurrencia")
    op.drop_column("task", "recurrencia")
