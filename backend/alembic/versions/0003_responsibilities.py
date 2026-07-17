"""responsabilidades: tabla responsibility

Revision ID: 0003_responsibilities
Revises: 0002_projects_tasks
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_responsibilities"
down_revision: str | None = "0002_projects_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "responsibility",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("recurrencia", sa.String(length=30), nullable=False),
        sa.Column("proximo_venc", sa.Date(), nullable=False),
        sa.Column("monto", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_responsibility_proximo_venc", "responsibility", ["proximo_venc"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_responsibility_proximo_venc", table_name="responsibility"
    )
    op.drop_table("responsibility")
