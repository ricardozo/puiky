"""Schemas Pydantic del dominio de proyectos."""

import uuid
from datetime import date
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
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class ProjectUpdate(BaseModel):
    """Actualización parcial: solo los campos enviados cambian. `portfolio_id`
    admite null explícito para sacar el proyecto de su portafolio."""

    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None
    estado: ProjectEstado | None = None
    portfolio_id: uuid.UUID | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    descripcion: str | None
    estado: str
    portfolio_id: uuid.UUID | None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    es_personal: bool = False
    # Derivados (los adjunta el servicio a partir de las tareas).
    total_tareas: int = 0
    tareas_terminadas: int = 0
    avance: int | None = None  # % (terminadas/total); None si no hay tareas


class ProjectDetailOut(ProjectOut):
    """Un proyecto con sus tareas y sus notas vinculadas."""

    tasks: list[TaskOut] = []
    notes: list[NoteOut] = []
