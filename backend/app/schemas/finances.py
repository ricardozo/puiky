"""Schemas Pydantic del dominio de finanzas."""

import uuid
from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TransactionTipo(str, Enum):
    gasto = "gasto"
    ingreso = "ingreso"
    transferencia = "transferencia"


# --- Cuentas ---


class AccountCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    # sugeridos: efectivo / banco / ahorros (extensible)
    tipo: str = Field(min_length=1, max_length=30)
    saldo_inicial: Decimal = Field(default=Decimal("0"))


class AccountUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    tipo: str | None = Field(default=None, min_length=1, max_length=30)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    tipo: str
    saldo: Decimal


# --- Categorías ---


class CategoryCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    activa: bool = True


class CategoryUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    activa: bool | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    activa: bool


# --- Movimientos ---


class TransactionCreate(BaseModel):
    tipo: TransactionTipo
    monto: Decimal = Field(gt=0)
    account_id: uuid.UUID
    cuenta_destino_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    fecha: date | None = None  # por defecto, hoy
    nota: str | None = Field(default=None, max_length=500)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: str
    monto: Decimal
    account_id: uuid.UUID
    cuenta_destino_id: uuid.UUID | None
    category_id: uuid.UUID | None
    fecha: date
    nota: str | None


# --- Reporte de gastos ---


class GastoPorCategoria(BaseModel):
    category_id: uuid.UUID | None
    categoria: str
    total: Decimal


class ReporteMensual(BaseModel):
    anio: int
    mes: int
    total_gastos: Decimal
    por_categoria: list[GastoPorCategoria]


# --- Presupuestos ---


class BudgetCreate(BaseModel):
    # sin category_id => presupuesto global del mes
    category_id: uuid.UUID | None = None
    tope: Decimal = Field(gt=0)
    periodo: str = "mensual"


class BudgetUpdate(BaseModel):
    tope: Decimal | None = Field(default=None, gt=0)
    periodo: str | None = None


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID | None
    tope: Decimal
    periodo: str


class BudgetProgress(BudgetOut):
    gastado: Decimal
    restante: Decimal
    porcentaje: float
