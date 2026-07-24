"""control: tabla whatsapp_link (vínculo WhatsApp → usuario)

Espejo de telegram_link para el canal de WhatsApp Cloud API. `wa_id` es el
número en formato internacional sin '+' (así lo entrega Meta en el webhook).

Revision ID: control_0003
Revises: control_0002
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "control_0003"
down_revision: str | None = "control_0002"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_link",
        sa.Column("wa_id", sa.String(length=20), primary_key=True),
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
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("whatsapp_link", schema="public")
