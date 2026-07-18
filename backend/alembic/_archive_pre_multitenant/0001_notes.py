"""notas: extensión pgvector + tablas note y note_link

Revision ID: 0001_notes
Revises:
Create Date: 2026-07-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "0001_notes"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Debe coincidir con EMBEDDING_DIM del .env y con el modelo Note.
# 768 = multilingual-e5-base.
EMBEDDING_DIM = 768


def upgrade() -> None:
    # Extensión para búsqueda semántica por vectores.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "note",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "creada",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "note_link",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column("entidad_tipo", sa.String(length=32), nullable=False),
        sa.Column("entidad_id", sa.UUID(), nullable=False),
        # Sin FK hacia project/task/... todavía: esas tablas no existen aún.
        sa.ForeignKeyConstraint(["note_id"], ["note.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_note_link_note_id", "note_link", ["note_id"])
    op.create_index(
        "ix_note_link_entidad", "note_link", ["entidad_tipo", "entidad_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_note_link_entidad", table_name="note_link")
    op.drop_index("ix_note_link_note_id", table_name="note_link")
    op.drop_table("note_link")
    op.drop_table("note")
    # La extensión vector no se elimina: podría usarla otro esquema.
