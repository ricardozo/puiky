"""Lógica de negocio del dominio de cuadernos."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notebooks import Notebook
from app.models.notes import Note
from app.schemas.notebooks import NotebookCreate, NotebookUpdate


def create_notebook(db: Session, data: NotebookCreate) -> Notebook:
    nb = Notebook(nombre=data.nombre, descripcion=data.descripcion)
    db.add(nb)
    db.commit()
    db.refresh(nb)
    return nb


def get_notebook(db: Session, notebook_id: uuid.UUID) -> Notebook | None:
    return db.get(Notebook, notebook_id)


def list_notebooks(db: Session) -> list[tuple[Notebook, int]]:
    """Cuadernos con su conteo de notas, ordenados por nombre."""
    conteo = (
        select(Note.notebook_id, func.count().label("n"))
        .group_by(Note.notebook_id)
        .subquery()
    )
    stmt = (
        select(Notebook, func.coalesce(conteo.c.n, 0))
        .join(conteo, conteo.c.notebook_id == Notebook.id, isouter=True)
        .order_by(Notebook.nombre)
    )
    return [(nb, int(n)) for nb, n in db.execute(stmt).all()]


def update_notebook(
    db: Session, notebook_id: uuid.UUID, data: NotebookUpdate
) -> Notebook | None:
    nb = db.get(Notebook, notebook_id)
    if nb is None:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(nb, campo, valor)
    db.commit()
    db.refresh(nb)
    return nb


def delete_notebook(db: Session, notebook_id: uuid.UUID) -> bool:
    """Elimina el cuaderno. Sus notas quedan sin cuaderno (FK SET NULL)."""
    nb = db.get(Notebook, notebook_id)
    if nb is None:
        return False
    db.delete(nb)
    db.commit()
    return True


def count_notes(db: Session, notebook_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count()).where(Note.notebook_id == notebook_id)
    ).scalar_one()
