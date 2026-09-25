"""dominio: marca de registro en transaction (orden dentro del mismo día)

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

`creado` = cuándo se registró el movimiento (no su fecha contable). Sirve para
ordenar los del mismo día: el último registrado, arriba.

Las filas existentes no tienen ese dato; se aproxima con el orden físico
(ctid), que sigue el orden de inserción salvo en filas editadas después.

Revision ID: domain_0015
Revises: domain_0014
Create Date: 2026-09-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "domain_0015"
down_revision: str | None = "domain_0014"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Sin default aún: así las filas existentes quedan en NULL y se rellenan
    # abajo, sin chocar con inquilinos donde el baseline ya creó la columna.
    op.execute('ALTER TABLE "transaction" ADD COLUMN IF NOT EXISTS creado TIMESTAMPTZ')
    op.execute(
        """
        UPDATE "transaction" t SET creado = x.aprox
        FROM (
            SELECT id,
                   fecha::timestamp
                   + row_number() OVER (PARTITION BY fecha ORDER BY ctid)
                     * interval '1 second' AS aprox
            FROM "transaction"
        ) x
        WHERE t.id = x.id AND t.creado IS NULL
        """
    )
    op.execute('ALTER TABLE "transaction" ALTER COLUMN creado SET DEFAULT now()')
    op.execute('ALTER TABLE "transaction" ALTER COLUMN creado SET NOT NULL')


def downgrade() -> None:
    op.drop_column("transaction", "creado")
