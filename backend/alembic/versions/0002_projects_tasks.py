"""proyectos y tareas: tablas project y task

Revision ID: 0002_projects_tasks
Revises: 0001_notes
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_projects_tasks"
down_revision: str | None = "0001_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "estado",
            sa.String(length=20),
            server_default=sa.text("'activo'"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "task",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column(
            "estado",
            sa.String(length=20),
            server_default=sa.text("'planeada'"),
            nullable=False,
        ),
        sa.Column(
            "avance_pct", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("fecha_limite", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_project_id", "task", ["project_id"])
    op.create_index("ix_task_estado", "task", ["estado"])
    op.create_index("ix_task_fecha_limite", "task", ["fecha_limite"])


def downgrade() -> None:
    op.drop_index("ix_task_fecha_limite", table_name="task")
    op.drop_index("ix_task_estado", table_name="task")
    op.drop_index("ix_task_project_id", table_name="task")
    op.drop_table("task")
    op.drop_table("project")
