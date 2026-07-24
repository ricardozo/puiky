"""Webhook del canal WhatsApp (Cloud API de Meta).

Espejo del bot de Telegram sobre los mismos servicios: texto o nota de voz →
NLU → acciones → respuesta; botones para confirmaciones. Meta exige responder
el webhook en segundos, así que se responde 200 de inmediato y el procesamiento
(LLM ~20 s) corre en background.

Memoria por conversación (historial y confirmaciones pendientes) vive en el
proceso, igual que en el bot de Telegram.
"""

from __future__ import annotations

import logging
import re
from collections import deque

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import text

from app import wa_client
from app.bot.client import PuikyClient
from app.config import get_settings
from app.database import SessionLocal
from app.models.users import WhatsappLink
from app.provision import vincular_wa_por_codigo

logger = logging.getLogger("puiky.wa")
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

_settings = get_settings()
_client = PuikyClient(_settings.puiky_api_url, _settings.service_token)

# Memoria en proceso (como chat_data en Telegram).
_HISTORIAL: dict[str, deque] = {}
_PENDIENTES_GASTO: dict[str, list[dict]] = {}
_VISTOS: deque = deque(maxlen=500)  # ids de mensajes ya procesados (reintentos)

_VINCULAR = re.compile(r"^/?vincular\s+(\S+)$", re.IGNORECASE)

BIENVENIDA = (
    "Hola, soy Puiky 🧠 — el corazón y la mente, el centro donde se piensa y "
    "se recuerda.\nAún no estás activado: si ya tienes usuario, envíame\n"
    "vincular <tu-código>"
)


def _resolver_user_id(wa_id: str) -> str | None:
    with SessionLocal() as db:
        db.execute(text("SET search_path TO public"))
        link = db.get(WhatsappLink, wa_id)
        if link is None or not link.activo:
            return None
        return str(link.user_id)


def _historial_de(wa_id: str) -> deque:
    return _HISTORIAL.setdefault(wa_id, deque(maxlen=8))


def _recordar(wa_id: str, entrada: str, respuesta: str) -> None:
    h = _historial_de(wa_id)
    h.append({"rol": "user", "texto": entrada})
    h.append({"rol": "assistant", "texto": respuesta})


def _extraer(res: dict, clave: str) -> list[dict]:
    return [
        a["resultado"][clave]
        for a in res.get("acciones", [])
        if isinstance(a.get("resultado"), dict) and a["resultado"].get(clave)
    ]


@router.get("/webhook")
def verificar(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
) -> PlainTextResponse:
    """Verificación del webhook (la hace Meta al configurarlo)."""
    s = get_settings()
    if hub_mode == "subscribe" and s.wa_verify_token and hub_token == s.wa_verify_token:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(403, "Token de verificación inválido")


@router.post("/webhook")
async def recibir(request: Request, tareas: BackgroundTasks) -> dict:
    """Recibe eventos de Meta. Responde 200 YA; procesa en background."""
    payload = await request.json()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                mid = msg.get("id")
                if mid and mid in _VISTOS:
                    continue  # reintento de Meta
                if mid:
                    _VISTOS.append(mid)
                tareas.add_task(_procesar_mensaje, msg)
    return {"status": "ok"}


async def _procesar_mensaje(msg: dict) -> None:
    wa_id = msg.get("from", "")
    tipo = msg.get("type")
    try:
        if tipo == "interactive":
            await _procesar_boton(wa_id, msg)
            return
        if tipo == "audio":
            audio = await wa_client.download_media(msg["audio"]["id"])
            if audio is None:
                await wa_client.send_text(wa_id, "No pude descargar el audio 😕")
                return
            texto = None
        elif tipo == "text":
            texto = (msg.get("text") or {}).get("body", "").strip()
            audio = None
        else:
            return  # stickers, imágenes, etc.: se ignoran por ahora

        # ¿Vinculación? (funciona aun sin estar activado)
        if texto:
            m = _VINCULAR.match(texto)
            if m:
                if _resolver_user_id(wa_id) is not None:
                    await wa_client.send_text(wa_id, "Ya estás activado 🙂")
                elif vincular_wa_por_codigo(wa_id, m.group(1)):
                    await wa_client.send_text(
                        wa_id,
                        "✅ ¡Listo! Ya puedes usar Puiky por WhatsApp. "
                        "Escríbeme o mándame un audio con lo que necesites.",
                    )
                else:
                    await wa_client.send_text(
                        wa_id, "Ese código no es válido o ya venció. Pide uno nuevo."
                    )
                return

        user_id = _resolver_user_id(wa_id)
        if user_id is None:
            await wa_client.send_text(wa_id, BIENVENIDA)
            return

        if audio is not None:
            texto = await _client.transcribe(audio, tenant_user=user_id)
            await wa_client.send_text(wa_id, f"🎙️ {texto}")

        res = await _client.interpret(
            texto, list(_historial_de(wa_id)), tenant_user=user_id
        )
        _recordar(wa_id, texto or "", res.get("respuesta") or "")
        await _responder(wa_id, res)
    except Exception:
        logger.exception("Error procesando mensaje de WhatsApp")
        await wa_client.send_text(wa_id, "Ups, tuve un problema procesando eso.")


async def _responder(wa_id: str, res: dict) -> None:
    """Igual que Telegram: confirmaciones con botones; si no, texto limpio."""
    borrados = _extraer(res, "confirmar")
    if borrados:
        for c in borrados:
            await wa_client.send_buttons(
                wa_id,
                f"¿Seguro que quieres borrar {c['que']}?",
                [(f"del:{c['tipo']}:{c['id']}", "🗑️ Sí, borrar"), ("cancel", "Cancelar")],
            )
        return
    gastos = _extraer(res, "confirmar_gasto")
    if gastos:
        _PENDIENTES_GASTO[wa_id] = gastos
        que = "; ".join(g["que"] for g in gastos)
        await wa_client.send_buttons(
            wa_id,
            f"⚠️ Es un monto alto. ¿Registro {que}?",
            [("gasto_ok", "✅ Sí, registrar"), ("cancel", "Cancelar")],
        )
        return
    await wa_client.send_text(
        wa_id, (res.get("respuesta") or "Hecho.").replace("**", "")
    )


async def _procesar_boton(wa_id: str, msg: dict) -> None:
    data = ((msg.get("interactive") or {}).get("button_reply") or {}).get("id", "")
    user_id = _resolver_user_id(wa_id)
    if user_id is None:
        return
    if data == "cancel":
        _PENDIENTES_GASTO.pop(wa_id, None)
        await wa_client.send_text(wa_id, "Cancelado.")
        return
    if data == "gasto_ok":
        pendientes = _PENDIENTES_GASTO.pop(wa_id, [])
        if not pendientes:
            await wa_client.send_text(wa_id, "Ya no tengo ese gasto pendiente.")
            return
        try:
            for g in pendientes:
                await _client.create_transaction(
                    {
                        "tipo": "gasto",
                        "monto": g["monto"],
                        "account_id": g["account_id"],
                        "category_id": g["category_id"],
                        "nota": g.get("nota"),
                    },
                    tenant_user=user_id,
                )
            await wa_client.send_text(wa_id, "✅ Registrado.")
        except Exception:
            logger.exception("Error registrando gasto confirmado (WA)")
            await wa_client.send_text(wa_id, "No pude registrarlo.")
        return
    if data.startswith("del:"):
        _, tipo, entidad_id = data.split(":", 2)
        try:
            await _client.delete_entity(tipo, entidad_id, tenant_user=user_id)
            await wa_client.send_text(wa_id, "🗑️ Borrado.")
        except Exception:
            logger.exception("Error borrando %s %s (WA)", tipo, entidad_id)
            await wa_client.send_text(wa_id, "No pude borrar eso.")
