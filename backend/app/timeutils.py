"""Utilidades de fecha/hora con zona horaria explícita.

Se usa ZoneInfo explícito (no la TZ del sistema) para que el cálculo sea igual
en Windows y Ubuntu. La zona se lee de la config (America/Bogota por defecto).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_settings


def zona() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def now_local() -> datetime:
    """Ahora, consciente de zona horaria (hora local del usuario)."""
    return datetime.now(zona())
