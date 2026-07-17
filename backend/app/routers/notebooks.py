"""Endpoints HTTP del dominio de cuadernos."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.notebooks import NotebookCreate, NotebookOut, NotebookUpdate
from app.services import notebooks as service

router = APIRouter(prefix="/notebooks", tags=["cuadernos"])


def _out(nb, notas: int) -> NotebookOut:
    return NotebookOut(
        id=nb.id,
        nombre=nb.nombre,
        descripcion=nb.descripcion,
        creada=nb.creada,
        notas=notas,
    )


@router.post("", response_model=NotebookOut, status_code=status.HTTP_201_CREATED)
def crear_cuaderno(
    data: NotebookCreate, db: Session = Depends(get_db)
) -> NotebookOut:
    return _out(service.create_notebook(db, data), 0)


@router.get("", response_model=list[NotebookOut])
def listar_cuadernos(db: Session = Depends(get_db)) -> list[NotebookOut]:
    """Cuadernos con su conteo de notas."""
    return [_out(nb, n) for nb, n in service.list_notebooks(db)]


@router.get("/{notebook_id}", response_model=NotebookOut)
def ver_cuaderno(
    notebook_id: uuid.UUID, db: Session = Depends(get_db)
) -> NotebookOut:
    nb = service.get_notebook(db, notebook_id)
    if nb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuaderno no encontrado")
    return _out(nb, service.count_notes(db, notebook_id))


@router.put("/{notebook_id}", response_model=NotebookOut)
def editar_cuaderno(
    notebook_id: uuid.UUID, data: NotebookUpdate, db: Session = Depends(get_db)
) -> NotebookOut:
    nb = service.update_notebook(db, notebook_id, data)
    if nb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuaderno no encontrado")
    return _out(nb, service.count_notes(db, notebook_id))


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuaderno(
    notebook_id: uuid.UUID, db: Session = Depends(get_db)
) -> None:
    """Elimina el cuaderno; sus notas quedan sin cuaderno."""
    if not service.delete_notebook(db, notebook_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuaderno no encontrado")
