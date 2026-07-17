"""Dependencia de autenticación para proteger los endpoints.

Acepta dos tipos de portador (ambos como `Authorization: Bearer <token>`):
- el token de servicio interno (llamante de confianza, p. ej. el bot);
- un JWT de sesión válido (usuario humano tras login).
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.security import verificar_token
from app.config import get_settings

_bearer = HTTPBearer(auto_error=False)


def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Devuelve el identificador del llamante ('service' o el usuario)."""
    if creds is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Falta autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = creds.credentials
    s = get_settings()
    if s.service_token and secrets_equal(token, s.service_token):
        return "service"
    usuario = verificar_token(token)
    if usuario is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def secrets_equal(a: str, b: str) -> bool:
    import secrets

    return secrets.compare_digest(a, b)
