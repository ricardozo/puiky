"""dominio: notas de tarea al cuaderno del proyecto de la tarea (backfill)

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

Complementa domain_0007: mueve las notas vinculadas a una TAREA al cuaderno del
proyecto de esa tarea (solo tareas con proyecto).

Revision ID: domain_0008
Revises: domain_0007
Create Date: 2026-07-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "domain_0008"
down_revision: str | None = "domain_0007"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 1) Cuaderno homónimo para proyectos con notas vinculadas vía sus tareas.
    op.execute(
        """
        INSERT INTO notebook (id, nombre, creada)
        SELECT gen_random_uuid(), p.nombre, now()
        FROM project p
        WHERE EXISTS (
            SELECT 1 FROM note_link nl
            JOIN task t ON t.id = nl.entidad_id
            WHERE nl.entidad_tipo = 'task' AND t.project_id = p.id
        )
        AND NOT EXISTS (
            SELECT 1 FROM notebook nb WHERE lower(nb.nombre) = lower(p.nombre)
        )
        """
    )
    # 2) Mueve las notas de tarea al cuaderno del proyecto de la tarea.
    op.execute(
        """
        UPDATE note SET notebook_id = nb.id
        FROM note_link nl
        JOIN task t ON t.id = nl.entidad_id AND nl.entidad_tipo = 'task'
        JOIN project p ON p.id = t.project_id
        JOIN notebook nb ON lower(nb.nombre) = lower(p.nombre)
        WHERE note.id = nl.note_id
          AND note.notebook_id IS DISTINCT FROM nb.id
        """
    )


def downgrade() -> None:
    pass
