"""dominio: fechas de inicio y fin en proyectos

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

Revision ID: domain_0006
Revises: domain_0005
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "domain_0006"
down_revision: str | None = "domain_0005"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # IF NOT EXISTS: en inquilinos recién aprovisionados el baseline ya las crea.
    op.execute("ALTER TABLE project ADD COLUMN IF NOT EXISTS fecha_inicio DATE")
    op.execute("ALTER TABLE project ADD COLUMN IF NOT EXISTS fecha_fin DATE")


def downgrade() -> None:
    op.drop_column("project", "fecha_fin")
    op.drop_column("project", "fecha_inicio")
