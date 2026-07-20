"""dominio: enlace de responsabilidad con finanzas (account_id, category_id)

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

Revision ID: domain_0004
Revises: domain_0003
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "domain_0004"
down_revision: str | None = "domain_0003"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "responsibility",
        sa.Column("account_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "responsibility",
        sa.Column("category_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_responsibility_account_id",
        "responsibility",
        "account",
        ["account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_responsibility_category_id",
        "responsibility",
        "category",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_responsibility_category_id", "responsibility", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_responsibility_account_id", "responsibility", type_="foreignkey"
    )
    op.drop_column("responsibility", "category_id")
    op.drop_column("responsibility", "account_id")
