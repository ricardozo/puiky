"""control: código de auto-vinculación de Telegram en app_user

Añade `enroll_code` (código de un solo uso) y `enroll_expira` a public.app_user.

Revision ID: control_0002
Revises: control_0001
Create Date: 2026-07-18
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "control_0002"
down_revision: str | None = "control_0001"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "app_user",
        sa.Column("enroll_code", sa.String(length=16), nullable=True),
        schema="public",
    )
    op.add_column(
        "app_user",
        sa.Column("enroll_expira", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_unique_constraint(
        "app_user_enroll_code_key", "app_user", ["enroll_code"], schema="public"
    )


def downgrade() -> None:
    op.drop_constraint(
        "app_user_enroll_code_key", "app_user", schema="public", type_="unique"
    )
    op.drop_column("app_user", "enroll_expira", schema="public")
    op.drop_column("app_user", "enroll_code", schema="public")
