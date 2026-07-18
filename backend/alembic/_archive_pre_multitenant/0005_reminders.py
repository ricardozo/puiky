"""recordatorios: tabla reminder

Revision ID: 0005_reminders
Revises: 0004_finances
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_reminders"
down_revision: str | None = "0004_finances"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reminder",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("origen_tipo", sa.String(length=20), nullable=True),
        sa.Column("origen_id", sa.UUID(), nullable=True),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("disparar_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "veces_avisado",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("pospuesto_para", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resuelto",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reminder_resuelto", "reminder", ["resuelto"])
    op.create_index("ix_reminder_disparar_en", "reminder", ["disparar_en"])


def downgrade() -> None:
    op.drop_index("ix_reminder_disparar_en", table_name="reminder")
    op.drop_index("ix_reminder_resuelto", table_name="reminder")
    op.drop_table("reminder")
