"""dominio: lista de mercado (market_product, market_purchase)

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

Revision ID: domain_0002
Revises: domain_0001
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "domain_0002"
down_revision: str | None = "domain_0001"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "market_product",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column(
            "unidad",
            sa.String(length=10),
            server_default=sa.text("'unidad'"),
            nullable=False,
        ),
        sa.Column("presentacion", sa.Numeric(12, 3), nullable=True),
        sa.Column("cadencia_dias", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "activo", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("notas", sa.String(length=300), nullable=True),
        sa.Column(
            "creada",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_index(
        "ix_market_product_category_id", "market_product", ["category_id"]
    )

    op.create_table(
        "market_purchase",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("product_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column(
            "cantidad", sa.Numeric(12, 3), server_default=sa.text("1"), nullable=False
        ),
        sa.Column("precio", sa.Numeric(14, 2), nullable=True),
        sa.Column(
            "creada",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["market_product.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_purchase_product_id", "market_purchase", ["product_id"]
    )
    op.create_index("ix_market_purchase_fecha", "market_purchase", ["fecha"])


def downgrade() -> None:
    op.drop_table("market_purchase")
    op.drop_table("market_product")
