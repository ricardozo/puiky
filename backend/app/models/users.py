"""Modelos de CONTROL (schema `public`), compartidos entre inquilinos.

- `User` (`app_user`): login web de cada persona + a qué schema de inquilino
  pertenece (`tenant_schema`).
- `TelegramLink`: mapa `telegram_id → app_user`. El bot lo usa para saber, en
  cada mensaje, en el contexto de qué usuario debe operar. Reemplaza al antiguo
  allowlist de IDs.

Ambas tablas quedan calificadas a `public` para que las consultas de control no
dependan del `search_path` (que apunta al schema del inquilino en cada request).
La contraseña se guarda siempre como hash, nunca en claro.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import ControlBase

_SCHEMA = {"schema": "public"}


class User(ControlBase):
    __tablename__ = "app_user"
    __table_args__ = _SCHEMA

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    usuario: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Schema de Postgres donde viven los datos de dominio de este usuario.
    tenant_schema: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    creado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TelegramLink(ControlBase):
    __tablename__ = "telegram_link"
    __table_args__ = _SCHEMA

    # El chat/usuario de Telegram es la clave: un ID → un usuario de Puiky.
    # BigInteger: los IDs de Telegram superan el rango de int32.
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.app_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    creado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
