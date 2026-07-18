"""Aislamiento por inquilino (schema-per-tenant).

Un ÚNICO punto decide en qué schema opera cada petición: `get_tenant_db`.
Autentica al llamante, resuelve su usuario y fija el `search_path` de la sesión
al schema de ese usuario. Los servicios y consultas de dominio no saben de
inquilinos: siguen siendo "de un solo usuario".

- Web: JWT (con `sub`); el usuario y su `tenant_schema` se validan contra
  `public.app_user` (fuente de verdad).
- Bot: token de servicio + cabecera `X-Tenant-User: <user_id>`.

Las consultas de control (`app_user`, `telegram_link`) van calificadas a
`public`, así que no dependen del `search_path`.
"""

from __future__ import annotations

import re
import secrets
import uuid
from collections.abc import Generator
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth.security import verificar_token_claims
from app.config import get_settings
from app.database import SessionLocal
from app.models.users import User

_bearer = HTTPBearer(auto_error=False)
_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


@dataclass
class Principal:
    """Quién hace la petición y en qué inquilino opera."""

    user_id: uuid.UUID
    usuario: str
    tenant_schema: str
    es_servicio: bool


def _set_search_path(db: Session, schema: str) -> None:
    if not _SCHEMA_RE.match(schema):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Schema de inquilino inválido")
    # schema ya validado contra la lista blanca del regex → seguro interpolar
    db.execute(text(f'SET search_path TO "{schema}", public'))


def _resolver_principal(
    db: Session, token: str, tenant_user: str | None
) -> Principal:
    s = get_settings()
    if s.service_token and secrets.compare_digest(token, s.service_token):
        if not tenant_user:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "El token de servicio requiere la cabecera X-Tenant-User",
            )
        try:
            uid = uuid.UUID(tenant_user)
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "X-Tenant-User inválido"
            ) from exc
        user = db.get(User, uid)
        es_servicio = True
    else:
        claims = verificar_token_claims(token)
        if claims is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = db.execute(
            select(User).where(User.usuario == claims.get("sub"))
        ).scalar_one_or_none()
        es_servicio = False

    if user is None or not user.activo:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado o inactivo"
        )
    return Principal(user.id, user.usuario, user.tenant_schema, es_servicio)


def get_tenant_db(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_tenant_user: str | None = Header(default=None, alias="X-Tenant-User"),
) -> Generator[Session, None, None]:
    """Sesión ya acotada al schema del inquilino autenticado.

    Reemplaza a `get_db` + `require_auth` en todos los routers de dominio.
    El `Principal` queda en `db.info['principal']` por si el endpoint lo necesita.
    """
    if creds is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Falta autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db = SessionLocal()
    try:
        principal = _resolver_principal(db, creds.credentials, x_tenant_user)
        _set_search_path(db, principal.tenant_schema)
        db.info["principal"] = principal
        yield db
    finally:
        db.close()


def get_control_db() -> Generator[Session, None, None]:
    """Sesión sobre el schema de control (`public`), sin autenticación previa.

    Para login y gestión de usuarios. Fija `search_path` a `public` por si la
    conexión del pool traía otro schema de una petición anterior."""
    db = SessionLocal()
    try:
        db.execute(text("SET search_path TO public"))
        yield db
    finally:
        db.close()
