"""dominio: cuaderno homónimo para todos los proyectos existentes (backfill)

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

Desde ahora el cuaderno de un proyecto nace CON el proyecto (no con su primera
nota vinculada), para que aparezca de inmediato como destino al guardar notas.
Este backfill crea el cuaderno de los proyectos que aún no lo tienen.

Revision ID: domain_0011
Revises: domain_0010
Create Date: 2026-07-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "domain_0011"
down_revision: str | None = "domain_0010"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO notebook (nombre, creada)
        SELECT p.nombre, now()
        FROM project p
        WHERE NOT EXISTS (
            SELECT 1 FROM notebook nb WHERE lower(nb.nombre) = lower(p.nombre)
        )
        """
    )


def downgrade() -> None:
    pass
