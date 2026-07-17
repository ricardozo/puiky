"""Modelo de usuario para el login de la interfaz web.

Sistema de un solo usuario, pero la interfaz web queda expuesta y requiere
autenticación. La contraseña se guarda siempre como hash, nunca en claro.
La tabla se llama `app_user` ('user' es palabra reservada en Postgres).
"""

import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    usuario: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    creado: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
