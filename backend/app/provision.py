"""Aprovisionamiento de inquilinos y usuarios (schema-per-tenant).

Crea el schema del inquilino, corre las migraciones de dominio dentro de él y
da de alta el usuario web en `public.app_user`. También enlaza cuentas de
Telegram (`public.telegram_link`).

Usado por los CLIs `app.create_user` y `app.link_telegram`, y por el script
`crear-usuario.sh`.
"""

from __future__ import annotations

import os
import re
import secrets
from argparse import Namespace
from datetime import datetime, timedelta, timezone

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.auth.security import hash_password
from app.database import SessionLocal, engine
from app.models.users import TelegramLink, User, WhatsappLink

_ALEMBIC_INI = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
_SLUG_RE = re.compile(r"^[a-z0-9_]{1,50}$")
_CODIGO_HORAS = 168  # el código de vinculación vive 7 días


def slug_a_schema(slug: str) -> str:
    if not _SLUG_RE.match(slug):
        raise ValueError(
            "Slug inválido: usa minúsculas, números y guion bajo (máx 50)."
        )
    return f"t_{slug}"


def _cfg(xargs: list[str]) -> Config:
    cfg = Config(_ALEMBIC_INI)
    cfg.cmd_opts = Namespace(x=xargs)  # env.py lee context.get_x_argument()
    return cfg


def upgrade_control() -> None:
    """Aplica la cadena de control (public). Idempotente."""
    command.upgrade(_cfg(["control=1"]), "control@head")


def upgrade_tenant(schema: str) -> None:
    """Aplica las migraciones de dominio dentro del schema del inquilino."""
    command.upgrade(_cfg([f"tenant={schema}"]), "domain@head")


def provision_tenant(slug: str) -> str:
    """Crea el schema del inquilino (si falta) y lo migra a head. Devuelve el
    nombre del schema."""
    schema = slug_a_schema(slug)
    with engine.connect() as c:
        c.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        c.commit()
    upgrade_tenant(schema)
    return schema


def _nuevo_codigo() -> tuple[str, datetime]:
    return secrets.token_hex(4), datetime.now(timezone.utc) + timedelta(
        hours=_CODIGO_HORAS
    )


def crear_usuario(usuario: str, password: str, slug: str) -> tuple[str, str, str]:
    """Provisiona el inquilino, crea/actualiza el usuario web y le genera un
    código de vinculación de Telegram. Devuelve (schema, accion, codigo)."""
    schema = provision_tenant(slug)
    code, expira = _nuevo_codigo()
    with SessionLocal() as db:
        db.execute(text("SET search_path TO public"))
        user = db.query(User).filter_by(usuario=usuario).first()
        if user is not None:
            user.password_hash = hash_password(password)
            accion = "actualizado"
        else:
            user = User(
                usuario=usuario,
                password_hash=hash_password(password),
                tenant_schema=schema,
            )
            db.add(user)
            accion = "creado"
        user.enroll_code = code
        user.enroll_expira = expira
        db.commit()
    return schema, accion, code


def generar_codigo(usuario: str) -> str:
    """Regenera el código de vinculación de un usuario existente."""
    code, expira = _nuevo_codigo()
    with SessionLocal() as db:
        db.execute(text("SET search_path TO public"))
        user = db.query(User).filter_by(usuario=usuario).first()
        if user is None:
            raise ValueError(f"El usuario '{usuario}' no existe.")
        user.enroll_code = code
        user.enroll_expira = expira
        db.commit()
    return code


def vincular_wa_por_codigo(wa_id: str, code: str) -> bool:
    """Enlaza un WhatsApp a un usuario con el mismo código de un solo uso que
    Telegram. Devuelve True si vinculó."""
    with SessionLocal() as db:
        db.execute(text("SET search_path TO public"))
        user = db.query(User).filter_by(enroll_code=code).first()
        if user is None or not user.activo:
            return False
        if user.enroll_expira is None or user.enroll_expira < datetime.now(
            timezone.utc
        ):
            return False
        link = db.get(WhatsappLink, wa_id)
        if link is not None:
            link.user_id = user.id
            link.activo = True
        else:
            db.add(WhatsappLink(wa_id=wa_id, user_id=user.id))
        user.enroll_code = None  # consumir
        user.enroll_expira = None
        db.commit()
        return True


def vincular_por_codigo(telegram_id: int, code: str) -> bool:
    """Enlaza un Telegram a un usuario si el código es válido y no venció.
    Consume el código (un solo uso). Devuelve True si vinculó."""
    with SessionLocal() as db:
        db.execute(text("SET search_path TO public"))
        user = db.query(User).filter_by(enroll_code=code).first()
        if user is None or not user.activo:
            return False
        if user.enroll_expira is None or user.enroll_expira < datetime.now(
            timezone.utc
        ):
            return False
        link = db.get(TelegramLink, telegram_id)
        if link is not None:
            link.user_id = user.id
            link.activo = True
        else:
            db.add(TelegramLink(telegram_id=telegram_id, user_id=user.id))
        user.enroll_code = None  # consumir
        user.enroll_expira = None
        db.commit()
        return True


def link_telegram(usuario: str, telegram_id: int) -> None:
    """Enlaza un ID de Telegram a un usuario (para que el bot lo reconozca)."""
    with SessionLocal() as db:
        db.execute(text("SET search_path TO public"))
        user = db.query(User).filter_by(usuario=usuario).first()
        if user is None:
            raise ValueError(f"El usuario '{usuario}' no existe.")
        link = db.get(TelegramLink, telegram_id)
        if link is not None:
            link.user_id = user.id
            link.activo = True
        else:
            db.add(TelegramLink(telegram_id=telegram_id, user_id=user.id))
        db.commit()
