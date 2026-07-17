"""Handlers del bot de Telegram."""

from __future__ import annotations

import logging

from telegram import Update
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


async def texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _bloquear_no_autorizado(update):
        return
    await update.effective_chat.send_action(ChatAction.TYPING)
    try:
        res = await _client.interpret(update.message.text)
        await update.message.reply_text(res.get("respuesta") or "Hecho.")
    except Exception:
        logger.exception("Error interpretando texto")
        await update.message.reply_text("Ups, tuve un problema procesando eso.")


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
        respuesta = res.get("respuesta") or "Hecho."
        await update.message.reply_text(
            f"🎙️ _{transcrito}_\n\n{respuesta}", parse_mode="Markdown"
        )
    except Exception:
        logger.exception("Error procesando audio")
        await update.message.reply_text("Ups, no pude procesar el audio.")
