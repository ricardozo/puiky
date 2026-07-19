"""dominio: modo compra (shopping_trip, trip_item)

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

Revision ID: domain_0003
Revises: domain_0002
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "domain_0003"
down_revision: str | None = "domain_0002"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "shopping_trip",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "estado",
            sa.String(length=10),
            server_default=sa.text("'abierta'"),
            nullable=False,
        ),
        sa.Column("total", sa.Numeric(14, 2), nullable=True),
        sa.Column("account_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "creada",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transaction.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "trip_item",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("trip_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column(
            "cantidad", sa.Numeric(12, 3), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("tamano", sa.String(length=40), nullable=True),
        sa.Column("precio", sa.Numeric(14, 2), nullable=True),
        sa.Column(
            "comprado", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("orden", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "creada",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["shopping_trip.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["market_product.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trip_item_trip_id", "trip_item", ["trip_id"])


def downgrade() -> None:
    op.drop_table("trip_item")
    op.drop_table("shopping_trip")
