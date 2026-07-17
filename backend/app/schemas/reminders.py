"""Schemas Pydantic del dominio de recordatorios."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReminderOrigen(str, Enum):
    task = "task"
    responsibility = "responsibility"
    budget = "budget"


class ReminderCreate(BaseModel):
    texto: str = Field(min_length=1)
    disparar_en: datetime
    origen_tipo: ReminderOrigen | None = None
    origen_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _origen_completo(self) -> "ReminderCreate":
        # Atado (ambos presentes) o suelto (ambos ausentes), nunca a medias.
        if (self.origen_tipo is None) != (self.origen_id is None):
            raise ValueError(
                "origen_tipo y origen_id deben ir juntos (o ninguno)"
            )
        return self


class ReminderUpdate(BaseModel):
    texto: str | None = Field(default=None, min_length=1)
    disparar_en: datetime | None = None


class ReminderSnooze(BaseModel):
    pospuesto_para: datetime


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    origen_tipo: str | None
    origen_id: uuid.UUID | None
    texto: str
    disparar_en: datetime
    veces_avisado: int
    pospuesto_para: datetime | None
    resuelto: bool
