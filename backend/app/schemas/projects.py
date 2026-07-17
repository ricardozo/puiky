"""Schemas Pydantic del dominio de proyectos."""

import uuid
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.notes import NoteOut
from app.schemas.tasks import TaskOut


class ProjectEstado(str, Enum):
    activo = "activo"
    pausado = "pausado"
    terminado = "terminado"


class ProjectCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None
    estado: ProjectEstado = ProjectEstado.activo


class ProjectUpdate(BaseModel):
    """Actualización parcial: solo los campos enviados cambian."""

    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None
    estado: ProjectEstado | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    descripcion: str | None
    estado: str


class ProjectDetailOut(ProjectOut):
    """Un proyecto con sus tareas y sus notas vinculadas."""

    tasks: list[TaskOut] = []
    notes: list[NoteOut] = []
