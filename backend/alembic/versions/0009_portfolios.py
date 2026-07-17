"""portafolios: tabla portfolio + project.portfolio_id

Revision ID: 0009_portfolios
Revises: 0008_note_titulo
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_portfolios"
down_revision: str | None = "0008_note_titulo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "creada",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("project", sa.Column("portfolio_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "project_portfolio_id_fkey",
        "project",
        "portfolio",
        ["portfolio_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_project_portfolio_id", "project", ["portfolio_id"])


def downgrade() -> None:
    op.drop_index("ix_project_portfolio_id", table_name="project")
    op.drop_constraint("project_portfolio_id_fkey", "project", type_="foreignkey")
    op.drop_column("project", "portfolio_id")
    op.drop_table("portfolio")
