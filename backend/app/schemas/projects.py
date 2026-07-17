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
    portfolio_id: uuid.UUID | None = None


class ProjectUpdate(BaseModel):
    """Actualización parcial: solo los campos enviados cambian. `portfolio_id`
    admite null explícito para sacar el proyecto de su portafolio."""

    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None
    estado: ProjectEstado | None = None
    portfolio_id: uuid.UUID | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    descripcion: str | None
    estado: str
    portfolio_id: uuid.UUID | None


class ProjectDetailOut(ProjectOut):
    """Un proyecto con sus tareas y sus notas vinculadas."""

    tasks: list[TaskOut] = []
    notes: list[NoteOut] = []
