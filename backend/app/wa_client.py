"""Cliente de la WhatsApp Cloud API (Graph API de Meta).

Solo lo que Puiky necesita: enviar texto, enviar botones de confirmación y
descargar medios (notas de voz). El webhook vive en `routers/whatsapp.py`.
"""

from __future__ import annotations

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("puiky.wa")

_GRAPH = "https://graph.facebook.com/v21.0"
_TIMEOUT = httpx.Timeout(30.0)


def _headers() -> dict:
    return {"Authorization": f"Bearer {get_settings().wa_access_token}"}


async def send_text(to: str, body: str) -> None:
    """Envía un mensaje de texto libre (válido dentro de la ventana de 24 h)."""
    s = get_settings()
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(
            f"{_GRAPH}/{s.wa_phone_number_id}/messages",
            headers=_headers(),
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": body[:4096]},
            },
        )
        if r.status_code >= 400:
            logger.error("WA send_text %s: %s", r.status_code, r.text[:300])


async def send_buttons(to: str, body: str, botones: list[tuple[str, str]]) -> None:
    """Envía botones de respuesta rápida (máx. 3): [(id, título), …]."""
    s = get_settings()
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(
            f"{_GRAPH}/{s.wa_phone_number_id}/messages",
            headers=_headers(),
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body[:1024]},
                    "action": {
                        "buttons": [
                            {
                                "type": "reply",
                                "reply": {"id": bid[:256], "title": titulo[:20]},
                            }
                            for bid, titulo in botones[:3]
                        ]
                    },
                },
            },
        )
        if r.status_code >= 400:
            logger.error("WA send_buttons %s: %s", r.status_code, r.text[:300])


async def download_media(media_id: str) -> bytes | None:
    """Descarga un medio (p. ej. nota de voz): primero la URL, luego el binario."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.get(f"{_GRAPH}/{media_id}", headers=_headers())
        if r.status_code >= 400:
            logger.error("WA media url %s: %s", r.status_code, r.text[:200])
            return None
        url = r.json().get("url")
        if not url:
            return None
        r2 = await c.get(url, headers=_headers())
        if r2.status_code >= 400:
            logger.error("WA media dl %s", r2.status_code)
            return None
        return r2.content
