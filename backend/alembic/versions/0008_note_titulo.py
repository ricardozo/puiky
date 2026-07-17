"""hojas: note.titulo + note.actualizada

Revision ID: 0008_note_titulo
Revises: 0007_notebooks
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_note_titulo"
down_revision: str | None = "0007_notebooks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("note", sa.Column("titulo", sa.String(length=200), nullable=True))
    op.add_column(
        "note",
        sa.Column(
            "actualizada",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("note", "actualizada")
    op.drop_column("note", "titulo")
