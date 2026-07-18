"""Tests del bot que no requieren Telegram vivo ni BD.

La autorización pasó de allowlist en .env a la tabla `telegram_link` (resolución
por BD, se prueba en integración). Aquí se cubre lo unitario: que las llamadas a
la API lleven el inquilino (`X-Tenant-User`) y el parseo de confirmaciones.
"""

from app.bot.client import PuikyClient
from app.bot.handlers import _confirmaciones


def test_headers_incluyen_tenant() -> None:
    c = PuikyClient("http://x", "tok-servicio")
    h = c._hdr("user-123")
    assert h["Authorization"] == "Bearer tok-servicio"
    assert h["X-Tenant-User"] == "user-123"


def test_headers_sin_tenant() -> None:
    c = PuikyClient("http://x", "tok-servicio")
    h = c._hdr(None)
    assert h["Authorization"] == "Bearer tok-servicio"
    assert "X-Tenant-User" not in h


def test_confirmaciones_extrae_borrados() -> None:
    res = {
        "acciones": [
            {"resultado": {"confirmar": {"tipo": "note", "id": "1", "que": "la nota X"}}},
            {"resultado": {"ok": True}},
        ]
    }
    confs = _confirmaciones(res)
    assert len(confs) == 1
    assert confs[0]["tipo"] == "note"
    assert confs[0]["que"] == "la nota X"


def test_confirmaciones_vacio() -> None:
    assert _confirmaciones({"acciones": []}) == []
    assert _confirmaciones({}) == []
