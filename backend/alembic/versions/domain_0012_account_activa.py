"""dominio: cuentas archivables (activa)

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

Una cuenta con movimientos no se puede borrar sin romper el histórico; en vez
de eso se archiva (activa=false): desaparece de las listas pero sus movimientos
siguen contando la historia.

Revision ID: domain_0012
Revises: domain_0011
Create Date: 2026-08-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "domain_0012"
down_revision: str | None = "domain_0011"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # IF NOT EXISTS: en inquilinos recién aprovisionados el baseline ya la crea.
    op.execute(
        "ALTER TABLE account ADD COLUMN IF NOT EXISTS activa BOOLEAN "
        "NOT NULL DEFAULT true"
    )


def downgrade() -> None:
    op.drop_column("account", "activa")
