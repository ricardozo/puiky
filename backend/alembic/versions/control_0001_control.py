"""control: extension pgvector + app_user + telegram_link (schema public)

Cadena de CONTROL (branch 'control'). Vive en `public`, compartida por todos
los inquilinos. Se aplica con:  alembic -x control=1 upgrade control@head

Revision ID: control_0001
Revises:
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "control_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = ("control",)
depends_on: str | None = None


def upgrade() -> None:
    # Extensión global de vectores (una vez por base, en public).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector SCHEMA public")

    op.create_table(
        "app_user",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("usuario", sa.String(length=60), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("tenant_schema", sa.String(length=63), nullable=False),
        sa.Column(
            "activo", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "creado",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario"),
        sa.UniqueConstraint("tenant_schema"),
        schema="public",
    )

    op.create_table(
        "telegram_link",
        sa.Column("telegram_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "activo", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "creado",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["public.app_user.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("telegram_id"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("telegram_link", schema="public")
    op.drop_table("app_user", schema="public")
    # La extensión vector no se elimina (puede usarla otro schema).
