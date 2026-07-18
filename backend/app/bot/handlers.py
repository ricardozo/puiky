"""Handlers del bot de Telegram (multi-usuario).

Cada mensaje se resuelve por `telegram_id → usuario` (tabla `public.telegram_link`)
y todas las llamadas a la API llevan `X-Tenant-User`, así el backend opera en el
schema de esa persona. Un remitente sin enlace queda fuera (reemplaza al antiguo
allowlist de IDs).
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from app.bot.client import PuikyClient
from app.config import get_settings
from app.database import SessionLocal
from app.models.users import TelegramLink

logger = logging.getLogger("puiky.bot")

_settings = get_settings()
_client = PuikyClient(_settings.puiky_api_url, _settings.service_token)

BIENVENIDA = (
    "*Hola, soy Puiky*\n"
    "El corazón y la mente, el centro donde se piensa y se recuerda.\n"
    "Puedo guardar tus notas, organizar tareas y proyectos, llevar tus finanzas "
    "y recordarte lo que importa. Háblame con naturalidad —por texto o por "
    "audio— y yo me encargo.\n"
    "¿Por dónde quieres empezar?"
)


def resolver_user_id(telegram_id: int | None) -> str | None:
    """Devuelve el id del usuario de Puiky enlazado a ese Telegram, o None."""
    if telegram_id is None:
        return None
    with SessionLocal() as db:
        db.execute(text("SET search_path TO public"))
        link = db.get(TelegramLink, telegram_id)
        if link is None or not link.activo:
            return None
        return str(link.user_id)


async def _resolver_o_bloquear(update: Update) -> str | None:
    """Resuelve el usuario del remitente; si no está enlazado, avisa y corta."""
    uid = update.effective_user.id if update.effective_user else None
    user_id = resolver_user_id(uid)
    if user_id is None:
        if update.message:
            await update.message.reply_text(
                "No estás autorizado para usar este bot.\n"
                f"Tu ID de Telegram es: {uid}\n"
                "Pídele al administrador que te dé de alta con ese ID."
            )
        logger.info("Mensaje de ID no enlazado: %s", uid)
    return user_id


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _resolver_o_bloquear(update) is None:
        return
    await update.message.reply_text(BIENVENIDA, parse_mode="Markdown")


def _confirmaciones(res: dict) -> list[dict]:
    """Extrae las peticiones de confirmación de borrado del resultado."""
    return [
        a["resultado"]["confirmar"]
        for a in res.get("acciones", [])
        if isinstance(a.get("resultado"), dict) and a["resultado"].get("confirmar")
    ]


async def _responder_interpretacion(update: Update, res: dict) -> None:
    """Si hay borrados por confirmar, muestra SOLO la pregunta con botones (el
    texto del modelo puede afirmar erróneamente que ya borró). Si no, responde."""
    confirmaciones = _confirmaciones(res)
    if confirmaciones:
        for c in confirmaciones:
            teclado = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🗑️ Sí, borrar", callback_data=f"del:{c['tipo']}:{c['id']}"
                        ),
                        InlineKeyboardButton("Cancelar", callback_data="cancel"),
                    ]
                ]
            )
            await update.message.reply_text(
                f"¿Seguro que quieres borrar {c['que']}?", reply_markup=teclado
            )
        return
    await update.message.reply_text(res.get("respuesta") or "Hecho.")


_MAX_HISTORIAL = 8  # últimos 8 mensajes (~4 intercambios)


def _historial(context: ContextTypes.DEFAULT_TYPE) -> list[dict]:
    return context.chat_data.setdefault("historial", [])


def _recordar(context, entrada: str, respuesta: str) -> None:
    hist = _historial(context)
    hist.append({"rol": "user", "texto": entrada})
    hist.append({"rol": "assistant", "texto": respuesta})
    context.chat_data["historial"] = hist[-_MAX_HISTORIAL:]


async def _procesar(update: Update, context, entrada: str, user_id: str) -> None:
    """Interpreta `entrada` en el contexto del usuario y responde."""
    res = await _client.interpret(entrada, _historial(context), tenant_user=user_id)
    _recordar(context, entrada, res.get("respuesta") or "")
    await _responder_interpretacion(update, res)


async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = await _resolver_o_bloquear(update)
    if user_id is None:
        return
    await update.effective_chat.send_action(ChatAction.TYPING)
    try:
        await _procesar(update, context, update.message.text, user_id)
    except Exception:
        logger.exception("Error interpretando texto")
        await update.message.reply_text("Ups, tuve un problema procesando eso.")


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los botones de confirmación de borrado."""
    q = update.callback_query
    await q.answer()
    user_id = resolver_user_id(q.from_user.id if q.from_user else None)
    if user_id is None:
        return
    data = q.data or ""
    if data == "cancel":
        await q.edit_message_text("Cancelado.")
        return
    if data.startswith("del:"):
        _, tipo, entidad_id = data.split(":", 2)
        try:
            await _client.delete_entity(tipo, entidad_id, tenant_user=user_id)
            await q.edit_message_text("🗑️ Borrado.")
        except Exception:
            logger.exception("Error borrando %s %s", tipo, entidad_id)
            await q.edit_message_text("No pude borrar eso.")


async def voz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = await _resolver_o_bloquear(update)
    if user_id is None:
        return
    await update.effective_chat.send_action(ChatAction.TYPING)
    try:
        media = update.message.voice or update.message.audio
        archivo = await media.get_file()
        audio = bytes(await archivo.download_as_bytearray())
        transcrito = await _client.transcribe(audio, tenant_user=user_id)
        await update.message.reply_text(f"🎙️ _{transcrito}_", parse_mode="Markdown")
        await _procesar(update, context, transcrito, user_id)
    except Exception:
        logger.exception("Error procesando audio")
        await update.message.reply_text("Ups, no pude procesar el audio.")
