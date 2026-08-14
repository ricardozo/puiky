"""Schemas Pydantic del registro de tiempo."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TimeEntryStart(BaseModel):
    task_id: uuid.UUID
    nota: str | None = Field(default=None, max_length=300)
    # Pomodoro pactado para ESTA sesión; el scheduler avisa por Telegram al
    # cumplirse. None = sin aviso.
    aviso_min: int | None = Field(default=None, ge=5, le=240)


class TimeEntryUpdate(BaseModel):
    """Corrección manual de una sesión (olvidé parar, me quedé dormido…)."""

    inicio: datetime | None = None
    fin: datetime | None = None
    nota: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _rango_coherente(self) -> "TimeEntryUpdate":
        if self.inicio and self.fin and self.fin <= self.inicio:
            raise ValueError("El fin debe ser posterior al inicio")
        return self


class TimeEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    inicio: datetime
    fin: datetime | None
    nota: str | None
    # Para mostrar (los adjunta el servicio).
    tarea: str | None = None
    proyecto: str | None = None
    project_id: uuid.UUID | None = None
