"""tareas: descripcion + notas

Revision ID: 0011_task_desc_notas
Revises: 0010_task_checklist_fechas
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_task_desc_notas"
down_revision: str | None = "0010_task_checklist_fechas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("task", sa.Column("descripcion", sa.Text(), nullable=True))
    op.add_column("task", sa.Column("notas", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("task", "notas")
    op.drop_column("task", "descripcion")
