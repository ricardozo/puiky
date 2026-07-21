"""Schemas Pydantic del dominio de cuadernos."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotebookCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = None


class NotebookUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    descripcion: str | None = None


class NotebookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    descripcion: str | None
    creada: datetime
    notas: int = 0  # cuántas notas contiene
    es_proyecto: bool = False  # cuaderno homónimo de un proyecto
