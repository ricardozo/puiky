"""Schemas Pydantic del dominio de responsabilidades."""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.recurrence import es_recurrencia_valida

_AYUDA_REC = "diaria | semanal | mensual | trimestral | anual | cada_<N>_dias"


class ResponsibilityCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    recurrencia: str = Field(description=_AYUDA_REC)
    proximo_venc: date
    monto: Decimal | None = Field(default=None, ge=0)
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None

    @field_validator("recurrencia")
    @classmethod
    def _validar_recurrencia(cls, v: str) -> str:
        if not es_recurrencia_valida(v):
            raise ValueError(f"Recurrencia inválida. Use: {_AYUDA_REC}")
        return v


class ResponsibilityUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    recurrencia: str | None = None
    proximo_venc: date | None = None
    monto: Decimal | None = Field(default=None, ge=0)
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None

    @field_validator("recurrencia")
    @classmethod
    def _validar_recurrencia(cls, v: str | None) -> str | None:
        if v is not None and not es_recurrencia_valida(v):
            raise ValueError(f"Recurrencia inválida. Use: {_AYUDA_REC}")
        return v


class ResponsibilityPay(BaseModel):
    """Datos opcionales al registrar el pago (sobrescriben lo guardado)."""

    monto: Decimal | None = Field(default=None, ge=0)
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None


class ResponsibilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    recurrencia: str
    proximo_venc: date
    monto: Decimal | None
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    # Nombres para mostrar (los adjunta el servicio).
    cuenta: str | None = None
    categoria: str | None = None


class ResponsibilityPayResult(BaseModel):
    """Resultado de registrar un pago: la responsabilidad avanzada y, si aplicó,
    el gasto creado en finanzas."""

    responsabilidad: ResponsibilityOut
    gasto_creado: bool = False
    monto: Decimal | None = None
    cuenta: str | None = None
    saldo_cuenta: Decimal | None = None
