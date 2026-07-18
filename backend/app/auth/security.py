"""Hashing de contraseñas (pbkdf2, stdlib) y emisión/validación de JWT."""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings

_ALGO = "HS256"
_PBKDF2_ITERS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERS)
    return "$".join(
        [
            "pbkdf2_sha256",
            str(_PBKDF2_ITERS),
            base64.b64encode(salt).decode(),
            base64.b64encode(dk).decode(),
        ]
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt_b64, hash_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        esperado = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iters))
        return secrets.compare_digest(dk, esperado)
    except (ValueError, TypeError):
        return False


def crear_token(usuario: str, tenant: str | None = None) -> str:
    s = get_settings()
    ahora = datetime.now(timezone.utc)
    payload: dict = {
        "sub": usuario,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=s.jwt_expire_minutes),
    }
    if tenant is not None:
        payload["tenant"] = tenant
    return jwt.encode(payload, s.jwt_secret, algorithm=_ALGO)


def verificar_token(token: str) -> str | None:
    """Devuelve el usuario (sub) si el token es válido, si no None."""
    claims = verificar_token_claims(token)
    return claims.get("sub") if claims else None


def verificar_token_claims(token: str) -> dict | None:
    """Devuelve el payload completo del JWT si es válido, si no None."""
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGO])
    except jwt.PyJWTError:
        return None
