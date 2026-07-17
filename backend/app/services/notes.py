"""Lógica de negocio del dominio de notas.

Esta capa NO conoce HTTP ni el canal (Telegram / web): recibe datos y una
sesión de BD y opera. Así la misma operación sirve a cualquier llamante.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.embeddings import get_embedder
from app.models.finances import Account
from app.models.notes import Note, NoteLink
from app.models.projects import Project
from app.models.responsibilities import Responsibility
from app.models.tasks import Task
from app.schemas.notes import NoteCreate, NoteLinkCreate, NoteUpdate

# Tipos de entidad cuyo destino se valida (todas sus tablas ya existen).
_MODELOS_VALIDABLES = {
    "project": Project,
    "task": Task,
    "responsibility": Responsibility,
    "account": Account,
}


def create_note(db: Session, data: NoteCreate) -> Note:
    """Crea una nota generando y guardando su embedding."""
    embedding = get_embedder().embed_document(data.contenido)
    note = Note(contenido=data.contenido, embedding=embedding)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_note(db: Session, note_id: uuid.UUID) -> Note | None:
    """Devuelve una nota con sus vínculos, o None si no existe."""
    stmt = (
        select(Note).options(selectinload(Note.links)).where(Note.id == note_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_notes(db: Session, limit: int = 50, offset: int = 0) -> list[Note]:
    """Lista notas, de la más reciente a la más antigua."""
    stmt = (
        select(Note).order_by(Note.creada.desc()).limit(limit).offset(offset)
    )
    return list(db.execute(stmt).scalars().all())


def update_note(db: Session, note_id: uuid.UUID, data: NoteUpdate) -> Note | None:
    """Edita el contenido y recalcula el embedding. None si no existe."""
    note = db.get(Note, note_id)
    if note is None:
        return None
    note.contenido = data.contenido
    note.embedding = get_embedder().embed_document(data.contenido)
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note_id: uuid.UUID) -> bool:
    """Elimina una nota (y sus vínculos, por cascada). False si no existe."""
    note = db.get(Note, note_id)
    if note is None:
        return False
    db.delete(note)
    db.commit()
    return True


def add_link(
    db: Session, note_id: uuid.UUID, data: NoteLinkCreate
) -> NoteLink | None:
    """Vincula la nota a otra entidad (polimórfico).

    Valida que el destino exista para los cuatro tipos (project / task /
    responsibility / account). Señala destino inexistente con ValueError,
    que el router traduce a 400.
    """
    note = db.get(Note, note_id)
    if note is None:
        return None
    tipo = data.entidad_tipo.value
    modelo = _MODELOS_VALIDABLES.get(tipo)
    if modelo is not None and db.get(modelo, data.entidad_id) is None:
        raise ValueError(f"La entidad {tipo} indicada no existe")
    link = NoteLink(
        note_id=note_id,
        entidad_tipo=tipo,
        entidad_id=data.entidad_id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def notes_for_entity(
    db: Session, entidad_tipo: str, entidad_id: uuid.UUID
) -> list[Note]:
    """Notas vinculadas a una entidad (p. ej. las notas de un proyecto)."""
    stmt = (
        select(Note)
        .join(NoteLink, NoteLink.note_id == Note.id)
        .where(
            NoteLink.entidad_tipo == entidad_tipo,
            NoteLink.entidad_id == entidad_id,
        )
        .order_by(Note.creada.desc())
    )
    return list(db.execute(stmt).scalars().unique().all())


def search_notes(
    db: Session, texto: str, limite: int = 5
) -> list[tuple[Note, float]]:
    """Búsqueda semántica: las notas más cercanas por significado.

    Ordena por distancia coseno en pgvector y devuelve (nota, similitud),
    donde similitud = 1 - distancia (1.0 = idéntico en significado).
    """
    query_vec = get_embedder().embed_query(texto)
    distancia = Note.embedding.cosine_distance(query_vec)
    stmt = select(Note, distancia.label("dist")).order_by(distancia).limit(limite)
    filas = db.execute(stmt).all()
    return [(nota, 1.0 - float(dist)) for nota, dist in filas]
