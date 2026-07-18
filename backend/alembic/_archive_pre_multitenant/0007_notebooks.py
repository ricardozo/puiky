"""cuadernos: tabla notebook + note.notebook_id

Revision ID: 0007_notebooks
Revises: 0006_users
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_notebooks"
down_revision: str | None = "0006_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notebook",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column(
            "creada",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("note", sa.Column("notebook_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "note_notebook_id_fkey",
        "note",
        "notebook",
        ["notebook_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_note_notebook_id", "note", ["notebook_id"])


def downgrade() -> None:
    op.drop_index("ix_note_notebook_id", table_name="note")
    op.drop_constraint("note_notebook_id_fkey", "note", type_="foreignkey")
    op.drop_column("note", "notebook_id")
    op.drop_table("notebook")
