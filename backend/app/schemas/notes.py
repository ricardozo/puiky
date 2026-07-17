"""Schemas Pydantic del dominio de notas (contratos de entrada/salida).

No exponen la columna `embedding`: es un detalle interno de la búsqueda
semántica, no parte del contrato de la API.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EntidadTipo(str, Enum):
    """Tipos válidos de entidad a la que una nota puede vincularse."""

    project = "project"
    task = "task"
    responsibility = "responsibility"
    account = "account"


# --- Notas ---


class NoteCreate(BaseModel):
    contenido: str = Field(min_length=1)


class NoteUpdate(BaseModel):
    contenido: str = Field(min_length=1)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contenido: str
    creada: datetime


# --- Vínculos ---


class NoteLinkCreate(BaseModel):
    entidad_tipo: EntidadTipo
    entidad_id: uuid.UUID


class NoteLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    note_id: uuid.UUID
    entidad_tipo: str
    entidad_id: uuid.UUID


class NoteWithLinksOut(NoteOut):
    links: list[NoteLinkOut] = []


# --- Búsqueda semántica ---


class SearchQuery(BaseModel):
    texto: str = Field(min_length=1)
    limite: int = Field(default=5, ge=1, le=50)


class SearchResult(NoteOut):
    # 1.0 = idéntico en significado; cerca de 0 = sin relación (coseno).
    similitud: float
