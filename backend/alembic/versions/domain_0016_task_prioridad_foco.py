"""dominio: prioridad y foco del día en task

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

`prioridad`: alta | media | baja (NULL = sin definir). `foco_fecha`: el día
en que la tarea se marcó como foco (⭐); solo cuenta si es HOY, así el foco se
limpia solo cada día sin procesos de fondo.

Revision ID: domain_0016
Revises: domain_0015
Create Date: 2026-09-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "domain_0016"
down_revision: str | None = "domain_0015"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # IF NOT EXISTS: en inquilinos recién aprovisionados el baseline ya las crea.
    op.execute("ALTER TABLE task ADD COLUMN IF NOT EXISTS prioridad VARCHAR(10) NULL")
    op.execute("ALTER TABLE task ADD COLUMN IF NOT EXISTS foco_fecha DATE NULL")


def downgrade() -> None:
    op.drop_column("task", "foco_fecha")
    op.drop_column("task", "prioridad")
