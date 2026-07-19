"""Schemas Pydantic de la lista de mercado."""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    unidad: str = Field(default="unidad", max_length=10)
    presentacion: Decimal | None = Field(default=None, gt=0)
    cadencia_dias: int | None = Field(default=None, gt=0)
    category_id: uuid.UUID | None = None
    notas: str | None = Field(default=None, max_length=300)


class ProductUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    unidad: str | None = Field(default=None, max_length=10)
    presentacion: Decimal | None = Field(default=None, gt=0)
    cadencia_dias: int | None = Field(default=None, gt=0)
    category_id: uuid.UUID | None = None
    activo: bool | None = None
    notas: str | None = Field(default=None, max_length=300)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    unidad: str
    presentacion: Decimal | None
    cadencia_dias: int | None
    category_id: uuid.UUID | None
    activo: bool
    notas: str | None
    # Derivados (los calcula el servicio):
    ultima_compra: date | None = None
    por_comprar: bool = False
    dias_desde: int | None = None


class PurchaseCreate(BaseModel):
    cantidad: Decimal = Field(default=Decimal("1"), gt=0)
    precio: Decimal | None = Field(default=None, ge=0)
    fecha: date | None = None  # por defecto, hoy


class PurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    fecha: date
    cantidad: Decimal
    precio: Decimal | None
