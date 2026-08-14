"""dominio: registro de tiempo (time_entry) + proyecto Vida con básicos

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

`time_entry` guarda sesiones de tiempo sobre tareas (fin NULL = corriendo).
Además se siembra un proyecto «Vida» con tareas permanentes (Tiempo en
familia, Entretenimiento individual, Estudio) para cronometrar la vida no
laboral; si el inquilino ya tiene un proyecto Vida, no se toca.

Revision ID: domain_0013
Revises: domain_0012
Create Date: 2026-08-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "domain_0013"
down_revision: str | None = "domain_0012"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    # IF NOT EXISTS: en inquilinos recién aprovisionados el baseline ya la crea.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS time_entry (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id UUID NOT NULL REFERENCES task(id) ON DELETE CASCADE,
            inicio TIMESTAMPTZ NOT NULL,
            fin TIMESTAMPTZ NULL,
            nota VARCHAR(300) NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_time_entry_task_id ON time_entry (task_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_time_entry_inicio ON time_entry (inicio)"
    )
    # Proyecto «Vida» + tareas básicas (solo si no existe ya).
    op.execute(
        """
        INSERT INTO project (nombre, descripcion)
        SELECT 'Vida',
               'Tiempo no laboral: familia, descanso, estudio. Sus tareas no se completan; acumulan tiempo.'
        WHERE NOT EXISTS (SELECT 1 FROM project WHERE lower(nombre) = 'vida')
        """
    )
    op.execute(
        """
        INSERT INTO task (titulo, project_id)
        SELECT t.titulo, p.id
        FROM (VALUES ('Tiempo en familia'), ('Entretenimiento individual'), ('Estudio')) AS t(titulo)
        JOIN project p ON lower(p.nombre) = 'vida'
        WHERE NOT EXISTS (
            SELECT 1 FROM task x
            WHERE x.project_id = p.id AND x.titulo = t.titulo
        )
        """
    )


def downgrade() -> None:
    op.drop_table("time_entry")
