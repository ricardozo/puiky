"""dominio: separar la cadencia de re-aviso del scheduler (proximo_aviso)

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

El scheduler reutilizaba `pospuesto_para` (posposición del usuario) para su
cadencia de re-avisos, lo que escondía de la web recordatorios vencidos entre un
aviso y el siguiente. Se agrega `proximo_aviso` para el scheduler y se limpia el
`pospuesto_para` de los no resueltos (bookkeeping viejo del scheduler) para que
lo vencido reaparezca de inmediato.

Revision ID: domain_0005
Revises: domain_0004
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "domain_0005"
down_revision: str | None = "domain_0004"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # IF NOT EXISTS: en inquilinos recién aprovisionados el baseline ya la crea.
    op.execute(
        "ALTER TABLE reminder ADD COLUMN IF NOT EXISTS proximo_aviso TIMESTAMPTZ"
    )
    # Resetea el bookkeeping viejo del scheduler (que vivía en pospuesto_para).
    op.execute(
        "UPDATE reminder SET pospuesto_para = NULL WHERE resuelto = false"
    )


def downgrade() -> None:
    op.drop_column("reminder", "proximo_aviso")
