"""dominio: aviso de pomodoro en time_entry

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

`aviso_min`: minutos de pomodoro pactados al iniciar la sesión (NULL = sin
aviso). `avisado`: el scheduler ya mandó el Telegram de esta sesión.

Revision ID: domain_0014
Revises: domain_0013
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "domain_0014"
down_revision: str | None = "domain_0013"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # IF NOT EXISTS: en inquilinos recién aprovisionados el baseline ya las crea.
    op.execute(
        "ALTER TABLE time_entry ADD COLUMN IF NOT EXISTS aviso_min INTEGER NULL"
    )
    op.execute(
        "ALTER TABLE time_entry ADD COLUMN IF NOT EXISTS avisado BOOLEAN "
        "NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.drop_column("time_entry", "avisado")
    op.drop_column("time_entry", "aviso_min")
