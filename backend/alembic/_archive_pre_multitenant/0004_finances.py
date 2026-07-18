"""finanzas: account, category, transaction, budget (+ categorías seed)

Revision ID: 0004_finances
Revises: 0003_responsibilities
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_finances"
down_revision: str | None = "0003_responsibilities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Conjunto inicial sugerido (extensible por API). Decisión confirmada.
CATEGORIAS_SEED = [
    "Comida",
    "Transporte",
    "Vivienda",
    "Servicios",
    "Salud",
    "Entretenimiento",
    "Compras",
    "Educación",
    "Salario",
    "Otros",
]


def upgrade() -> None:
    op.create_table(
        "account",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column(
            "saldo",
            sa.Numeric(precision=14, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "category",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column(
            "activa", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )

    op.create_table(
        "transaction",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(length=15), nullable=False),
        sa.Column("monto", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column("cuenta_destino_id", sa.UUID(), nullable=True),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("nota", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
        sa.ForeignKeyConstraint(["cuenta_destino_id"], ["account.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transaction_account_id", "transaction", ["account_id"])
    op.create_index("ix_transaction_category_id", "transaction", ["category_id"])
    op.create_index("ix_transaction_fecha", "transaction", ["fecha"])
    op.create_index("ix_transaction_tipo", "transaction", ["tipo"])

    op.create_table(
        "budget",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("tope", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "periodo",
            sa.String(length=20),
            server_default=sa.text("'mensual'"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budget_category_id", "budget", ["category_id"])

    # Seed de categorías sugeridas.
    categoria = sa.table("category", sa.column("nombre", sa.String))
    op.bulk_insert(categoria, [{"nombre": n} for n in CATEGORIAS_SEED])


def downgrade() -> None:
    op.drop_index("ix_budget_category_id", table_name="budget")
    op.drop_table("budget")
    op.drop_index("ix_transaction_tipo", table_name="transaction")
    op.drop_index("ix_transaction_fecha", table_name="transaction")
    op.drop_index("ix_transaction_category_id", table_name="transaction")
    op.drop_index("ix_transaction_account_id", table_name="transaction")
    op.drop_table("transaction")
    op.drop_table("category")
    op.drop_table("account")
