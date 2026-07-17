"""Endpoints HTTP del dominio de notas.

Capa delgada: valida entrada/salida y delega en `services.notes`. Ninguna
lógica de negocio vive aquí, y no asume quién llama (web o Telegram).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.notes import (
    NoteCreate,
    NoteLinkCreate,
    NoteLinkOut,
    NoteOut,
    NoteUpdate,
    NoteWithLinksOut,
    SearchQuery,
    SearchResult,
)
from app.services import notes as service

router = APIRouter(prefix="/notes", tags=["notas"])


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def crear_nota(data: NoteCreate, db: Session = Depends(get_db)) -> NoteOut:
    """Crea una nota y guarda su embedding para la búsqueda semántica."""
    try:
        return service.create_note(db, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post("/search", response_model=list[SearchResult])
def buscar_notas(
    query: SearchQuery, db: Session = Depends(get_db)
) -> list[SearchResult]:
    """Búsqueda semántica: devuelve las notas más cercanas por significado."""
    resultados = service.search_notes(db, query.texto, query.limite)
    return [
        SearchResult(
            id=nota.id,
            contenido=nota.contenido,
            notebook_id=nota.notebook_id,
            creada=nota.creada,
            similitud=similitud,
        )
        for nota, similitud in resultados
    ]


@router.get("", response_model=list[NoteOut])
def listar_notas(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    notebook_id: uuid.UUID | None = Query(default=None),
    sin_cuaderno: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[NoteOut]:
    """Lista notas. Filtra por `notebook_id`, o `sin_cuaderno=true` para las
    que no tienen cuaderno; sin filtro, todas."""
    if sin_cuaderno:
        return service.list_notes(db, limit, offset, notebook_id=None)
    if notebook_id is not None:
        return service.list_notes(db, limit, offset, notebook_id=notebook_id)
    return service.list_notes(db, limit, offset)


@router.get("/{note_id}", response_model=NoteWithLinksOut)
def ver_nota(
    note_id: uuid.UUID, db: Session = Depends(get_db)
) -> NoteWithLinksOut:
    """Devuelve una nota con sus vínculos."""
    nota = service.get_note(db, note_id)
    if nota is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nota no encontrada")
    return nota


@router.put("/{note_id}", response_model=NoteOut)
def editar_nota(
    note_id: uuid.UUID, data: NoteUpdate, db: Session = Depends(get_db)
) -> NoteOut:
    """Edita el contenido (recalcula embedding) y/o mueve la nota de cuaderno."""
    try:
        nota = service.update_note(db, note_id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if nota is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nota no encontrada")
    return nota


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_nota(note_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Elimina una nota (y sus vínculos, por cascada)."""
    if not service.delete_note(db, note_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nota no encontrada")


@router.post(
    "/{note_id}/links",
    response_model=NoteLinkOut,
    status_code=status.HTTP_201_CREATED,
)
def vincular_nota(
    note_id: uuid.UUID, data: NoteLinkCreate, db: Session = Depends(get_db)
) -> NoteLinkOut:
    """Vincula la nota a otra entidad (project / task / responsibility / account)."""
    try:
        link = service.add_link(db, note_id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nota no encontrada")
    return link
