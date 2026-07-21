"""Lógica de negocio del dominio de notas.

Esta capa NO conoce HTTP ni el canal (Telegram / web): recibe datos y una
sesión de BD y opera. Así la misma operación sirve a cualquier llamante.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.embeddings import get_embedder
from app.models.finances import Account
from app.models.notebooks import Notebook
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


def _validar_cuaderno(db: Session, notebook_id: uuid.UUID | None) -> None:
    if notebook_id is not None and db.get(Notebook, notebook_id) is None:
        raise ValueError("El cuaderno indicado no existe")


def _texto_embedding(titulo: str | None, contenido: str) -> str:
    """Se indexa título + cuerpo para encontrar la hoja por cualquiera."""
    return f"{titulo}\n{contenido}" if titulo else contenido


def create_note(db: Session, data: NoteCreate) -> Note:
    """Crea una hoja generando y guardando su embedding (título + cuerpo)."""
    _validar_cuaderno(db, data.notebook_id)
    embedding = get_embedder().embed_document(
        _texto_embedding(data.titulo, data.contenido)
    )
    note = Note(
        titulo=data.titulo,
        contenido=data.contenido,
        embedding=embedding,
        notebook_id=data.notebook_id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def append_note(db: Session, note_id: uuid.UUID, texto: str) -> Note | None:
    """Añade texto al cuerpo de una hoja (en una línea nueva) y re-indexa."""
    note = db.get(Note, note_id)
    if note is None:
        return None
    note.contenido = f"{note.contenido}\n{texto}"
    note.embedding = get_embedder().embed_document(
        _texto_embedding(note.titulo, note.contenido)
    )
    db.commit()
    db.refresh(note)
    return note


def get_note(db: Session, note_id: uuid.UUID) -> Note | None:
    """Devuelve una nota con sus vínculos, o None si no existe."""
    stmt = (
        select(Note).options(selectinload(Note.links)).where(Note.id == note_id)
    )
    return db.execute(stmt).scalar_one_or_none()


# Centinela para distinguir "sin cuaderno" (None) de "sin filtro".
_SIN_FILTRO = object()


def list_notes(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    notebook_id: uuid.UUID | None | object = _SIN_FILTRO,
) -> list[Note]:
    """Lista notas, de la más reciente a la más antigua. Filtra por cuaderno
    si se pasa `notebook_id` (None = solo las sin cuaderno)."""
    stmt = select(Note)
    if notebook_id is not _SIN_FILTRO:
        stmt = stmt.where(Note.notebook_id == notebook_id)
    stmt = stmt.order_by(Note.creada.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


def update_note(db: Session, note_id: uuid.UUID, data: NoteUpdate) -> Note | None:
    """Edita contenido (recalcula embedding) y/o mueve de cuaderno. Solo los
    campos enviados cambian. None si la nota no existe."""
    note = db.get(Note, note_id)
    if note is None:
        return None
    cambios = data.model_dump(exclude_unset=True)
    if "notebook_id" in cambios:
        _validar_cuaderno(db, cambios["notebook_id"])
        note.notebook_id = cambios["notebook_id"]
    reembeber = False
    if "titulo" in cambios:
        note.titulo = cambios["titulo"]
        reembeber = True
    if cambios.get("contenido"):
        note.contenido = cambios["contenido"]
        reembeber = True
    if reembeber:
        note.embedding = get_embedder().embed_document(
            _texto_embedding(note.titulo, note.contenido)
        )
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


def cuaderno_de_proyecto(db: Session, project: Project) -> Notebook:
    """Cuaderno homónimo del proyecto (lo crea si no existe). Las notas de un
    proyecto se agrupan ahí."""
    nb = db.execute(
        select(Notebook).where(func.lower(Notebook.nombre) == project.nombre.lower())
    ).scalar_one_or_none()
    if nb is None:
        nb = Notebook(nombre=project.nombre)
        db.add(nb)
        db.flush()
    return nb


def add_link(
    db: Session, note_id: uuid.UUID, data: NoteLinkCreate
) -> NoteLink | None:
    """Vincula la nota a otra entidad (polimórfico).

    Valida que el destino exista para los cuatro tipos (project / task /
    responsibility / account). Señala destino inexistente con ValueError,
    que el router traduce a 400. Si el destino es un proyecto, la nota queda en
    el cuaderno homónimo del proyecto.
    """
    note = db.get(Note, note_id)
    if note is None:
        return None
    tipo = data.entidad_tipo.value
    modelo = _MODELOS_VALIDABLES.get(tipo)
    entidad = db.get(modelo, data.entidad_id) if modelo is not None else None
    if modelo is not None and entidad is None:
        raise ValueError(f"La entidad {tipo} indicada no existe")
    if tipo == "project" and entidad is not None:
        note.notebook_id = cuaderno_de_proyecto(db, entidad).id
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
    """Notas vinculadas a una entidad (p. ej. las notas de un proyecto o tarea)."""
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


def delete_link_between(
    db: Session, note_id: uuid.UUID, entidad_tipo: str, entidad_id: uuid.UUID
) -> bool:
    """Desvincula una nota de una entidad (elimina ese NoteLink). La nota no se
    borra: solo deja de estar vinculada."""
    link = db.execute(
        select(NoteLink).where(
            NoteLink.note_id == note_id,
            NoteLink.entidad_tipo == entidad_tipo,
            NoteLink.entidad_id == entidad_id,
        )
    ).scalar_one_or_none()
    if link is None:
        return False
    db.delete(link)
    db.commit()
    return True


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
