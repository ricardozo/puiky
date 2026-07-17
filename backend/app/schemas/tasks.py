"""Schemas Pydantic del dominio de tareas."""

import uuid
from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TaskEstado(str, Enum):
    """Los cuatro estados son las columnas del Kanban."""

    planeada = "planeada"
    en_ejecucion = "en_ejecucion"
    en_pausa = "en_pausa"
    terminada = "terminada"


class TaskCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=300)
    project_id: uuid.UUID | None = None
    estado: TaskEstado = TaskEstado.planeada
    avance_pct: int = Field(default=0, ge=0, le=100)
    fecha_limite: date | None = None  # fin planeado (deadline)
    fecha_inicio_plan: date | None = None
    fecha_inicio_real: date | None = None
    fecha_fin_real: date | None = None


class TaskUpdate(BaseModel):
    """Actualización parcial: solo los campos enviados cambian.
    Los campos de fecha y `project_id` admiten null explícito para desasignar.
    """

    titulo: str | None = Field(default=None, min_length=1, max_length=300)
    project_id: uuid.UUID | None = None
    estado: TaskEstado | None = None
    avance_pct: int | None = Field(default=None, ge=0, le=100)
    fecha_limite: date | None = None
    fecha_inicio_plan: date | None = None
    fecha_inicio_real: date | None = None
    fecha_fin_real: date | None = None


class TaskProgress(BaseModel):
    avance_pct: int = Field(ge=0, le=100)


# --- Checklist ---


class ChecklistItemCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=300)


class ChecklistItemUpdate(BaseModel):
    texto: str | None = Field(default=None, min_length=1, max_length=300)
    hecho: bool | None = None


class ChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    texto: str
    hecho: bool
    orden: int


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID | None
    titulo: str
    estado: str
    avance_pct: int
    fecha_limite: date | None
    fecha_inicio_plan: date | None
    fecha_inicio_real: date | None
    fecha_fin_real: date | None
    checklist: list[ChecklistItemOut] = []
