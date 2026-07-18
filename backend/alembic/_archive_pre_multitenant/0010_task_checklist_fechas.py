"""tareas: checklist_item + fechas plan/real

Revision ID: 0010_task_checklist_fechas
Revises: 0009_portfolios
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_task_checklist_fechas"
down_revision: str | None = "0009_portfolios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Fechas de planeación/ejecución (fecha_limite ya existe = fin planeado).
    op.add_column("task", sa.Column("fecha_inicio_plan", sa.Date(), nullable=True))
    op.add_column("task", sa.Column("fecha_inicio_real", sa.Date(), nullable=True))
    op.add_column("task", sa.Column("fecha_fin_real", sa.Date(), nullable=True))

    op.create_table(
        "checklist_item",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("texto", sa.String(length=300), nullable=False),
        sa.Column(
            "hecho", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("orden", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_checklist_item_task_id", "checklist_item", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_checklist_item_task_id", table_name="checklist_item")
    op.drop_table("checklist_item")
    op.drop_column("task", "fecha_fin_real")
    op.drop_column("task", "fecha_inicio_real")
    op.drop_column("task", "fecha_inicio_plan")
