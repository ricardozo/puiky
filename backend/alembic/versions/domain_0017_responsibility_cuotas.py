"""dominio: cuotas en responsabilidades

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

`cuotas_restantes`: pagos que faltan (NULL = indefinida). Cada pago descuenta
una; al pagar la última, la responsabilidad desaparece como una «única».

Revision ID: domain_0017
Revises: domain_0016
Create Date: 2026-10-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "domain_0017"
down_revision: str | None = "domain_0016"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # IF NOT EXISTS: en inquilinos recién aprovisionados el baseline ya la crea.
    op.execute(
        "ALTER TABLE responsibility ADD COLUMN IF NOT EXISTS cuotas_restantes INTEGER NULL"
    )


def downgrade() -> None:
    op.drop_column("responsibility", "cuotas_restantes")
