"""Handlers del bot de Telegram."""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from app.bot.client import PuikyClient
from app.config import get_settings

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


def esta_autorizado(uid: int | None, allowed: set[int]) -> bool:
    """Lógica pura de la allowlist (testeable sin Telegram)."""
    return uid is not None and uid in allowed


async def _bloquear_no_autorizado(update: Update) -> bool:
    """Si el usuario no está autorizado, le responde con su ID y corta."""
    uid = update.effective_user.id if update.effective_user else None
    if esta_autorizado(uid, get_settings().allowed_ids):
        return False
    if update.message:
        await update.message.reply_text(
            "No estás autorizado para usar este bot.\n"
            f"Tu ID de Telegram es: {uid}\n"
            "Pídele al administrador que lo agregue a la allowlist."
        )
    logger.info("Mensaje de ID no autorizado: %s", uid)
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _bloquear_no_autorizado(update):
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


async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _bloquear_no_autorizado(update):
        return
    await update.effective_chat.send_action(ChatAction.TYPING)
    try:
        res = await _client.interpret(update.message.text)
        await _responder_interpretacion(update, res)
    except Exception:
        logger.exception("Error interpretando texto")
        await update.message.reply_text("Ups, tuve un problema procesando eso.")


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los botones de confirmación de borrado."""
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id if q.from_user else None
    if not esta_autorizado(uid, get_settings().allowed_ids):
        return
    data = q.data or ""
    if data == "cancel":
        await q.edit_message_text("Cancelado.")
        return
    if data.startswith("del:"):
        _, tipo, entidad_id = data.split(":", 2)
        try:
            await _client.delete_entity(tipo, entidad_id)
            await q.edit_message_text("🗑️ Borrado.")
        except Exception:
            logger.exception("Error borrando %s %s", tipo, entidad_id)
            await q.edit_message_text("No pude borrar eso.")


async def voz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _bloquear_no_autorizado(update):
        return
    await update.effective_chat.send_action(ChatAction.TYPING)
    try:
        media = update.message.voice or update.message.audio
        archivo = await media.get_file()
        audio = bytes(await archivo.download_as_bytearray())
        res = await _client.voice(audio)
        transcrito = res.get("texto", "")
        await update.message.reply_text(f"🎙️ _{transcrito}_", parse_mode="Markdown")
        await _responder_interpretacion(update, res)
    except Exception:
        logger.exception("Error procesando audio")
        await update.message.reply_text("Ups, no pude procesar el audio.")
