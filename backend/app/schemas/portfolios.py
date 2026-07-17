"""Schemas Pydantic del dominio de portafolios."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PortfolioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = None


class PortfolioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    descripcion: str | None = None


class PortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    descripcion: str | None
    creada: datetime
    proyectos: int = 0  # cuántos proyectos contiene
