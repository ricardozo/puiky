"""dominio: agrupar las notas de cada proyecto en un cuaderno homónimo (backfill)

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

Migración solo de datos: crea un cuaderno con el nombre de cada proyecto que ya
tenga notas vinculadas y mueve esas notas a ese cuaderno. De aquí en adelante,
`add_link` mantiene la regla al vincular nuevas notas a un proyecto.

Revision ID: domain_0007
Revises: domain_0006
Create Date: 2026-07-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "domain_0007"
down_revision: str | None = "domain_0006"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 1) Un cuaderno homónimo por proyecto con notas vinculadas (si no existe ya).
    op.execute(
        """
        INSERT INTO notebook (id, nombre, creada)
        SELECT gen_random_uuid(), p.nombre, now()
        FROM project p
        WHERE EXISTS (
            SELECT 1 FROM note_link nl
            WHERE nl.entidad_tipo = 'project' AND nl.entidad_id = p.id
        )
        AND NOT EXISTS (
            SELECT 1 FROM notebook nb WHERE lower(nb.nombre) = lower(p.nombre)
        )
        """
    )
    # 2) Mueve las notas vinculadas a un proyecto a su cuaderno homónimo.
    op.execute(
        """
        UPDATE note SET notebook_id = nb.id
        FROM note_link nl
        JOIN project p ON p.id = nl.entidad_id AND nl.entidad_tipo = 'project'
        JOIN notebook nb ON lower(nb.nombre) = lower(p.nombre)
        WHERE note.id = nl.note_id
          AND note.notebook_id IS DISTINCT FROM nb.id
        """
    )


def downgrade() -> None:
    # Migración de datos: no se revierte (no borramos cuadernos ni notas).
    pass
