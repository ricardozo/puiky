"""dominio: proyecto Personal (es_personal) + adopción de tareas huérfanas

Cadena de DOMINIO. Se aplica por cada inquilino:
    alembic -x tenant=t_<slug> upgrade domain@head

«Personal» es un proyecto real por inquilino (marcado con es_personal para
sobrevivir renombres): agrupa las tareas sin proyecto y les da Kanban, avance,
recurrencia y notas como a cualquier proyecto. Las tareas huérfanas existentes
se mueven a él.

Revision ID: domain_0010
Revises: domain_0009
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "domain_0010"
down_revision: str | None = "domain_0009"
branch_labels: Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "project",
        sa.Column(
            "es_personal",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    # Si ya existe un proyecto llamado «Personal», se adopta; si no, se crea.
    op.execute(
        """
        UPDATE project SET es_personal = true
        WHERE lower(nombre) = 'personal'
          AND NOT EXISTS (SELECT 1 FROM project WHERE es_personal)
        """
    )
    op.execute(
        """
        INSERT INTO project (nombre, es_personal)
        SELECT 'Personal', true
        WHERE NOT EXISTS (SELECT 1 FROM project WHERE es_personal)
        """
    )
    # Tareas huérfanas → Personal.
    op.execute(
        """
        UPDATE task
        SET project_id = (SELECT id FROM project WHERE es_personal LIMIT 1)
        WHERE project_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("project", "es_personal")
