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
from app.provision import vincular_por_codigo

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
                "Aún no estás activado en Puiky.\n"
                "Si ya tienes usuario, envía tu código:  /vincular <código>\n"
                f"(Tu ID de Telegram es: {uid})"
            )
        logger.info("Mensaje de ID no enlazado: %s", uid)
    return user_id


async def vincular(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Auto-vinculación con un código de un solo uso: /vincular <código>."""
    uid = update.effective_user.id if update.effective_user else None
    if resolver_user_id(uid) is not None:
        await update.message.reply_text("Ya estás activado 🙂")
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            "Para activarte, envía tu código:  /vincular <código>\n"
            "(te lo da quien administra Puiky)."
        )
        return
    if uid is not None and vincular_por_codigo(uid, args[0].strip()):
        await update.message.reply_text(
            "✅ ¡Listo! Ya puedes usar Puiky. Escríbeme lo que necesites."
        )
    else:
        await update.message.reply_text(
            "Ese código no es válido o ya venció. Pide uno nuevo."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _resolver_o_bloquear(update) is None:
        return
    await update.message.reply_text(BIENVENIDA, parse_mode="Markdown")


def _extraer(res: dict, clave: str) -> list[dict]:
    """Extrae del resultado las peticiones marcadas con `clave` (confirmar / confirmar_gasto)."""
    return [
        a["resultado"][clave]
        for a in res.get("acciones", [])
        if isinstance(a.get("resultado"), dict) and a["resultado"].get(clave)
    ]


def _confirmaciones(res: dict) -> list[dict]:
    """Peticiones de confirmación de borrado (compat)."""
    return _extraer(res, "confirmar")


async def _responder_interpretacion(
    update: Update, context: ContextTypes.DEFAULT_TYPE, res: dict
) -> None:
    """Muestra SOLO la pregunta con botones cuando hay algo por confirmar (borrados,
    o gastos de monto alto); el texto del modelo puede afirmar erróneamente que ya
    lo hizo. Si no, responde normal."""
    borrados = _extraer(res, "confirmar")
    if borrados:
        for c in borrados:
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

    gastos = _extraer(res, "confirmar_gasto")
    if gastos:
        context.chat_data["pending_gasto"] = gastos
        que = "; ".join(g["que"] for g in gastos)
        teclado = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Sí, registrar", callback_data="gasto_ok"),
                    InlineKeyboardButton("Cancelar", callback_data="cancel"),
                ]
            ]
        )
        await update.message.reply_text(
            f"⚠️ Es un monto alto. ¿Registro {que}?", reply_markup=teclado
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
    await _responder_interpretacion(update, context, res)


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
        context.chat_data.pop("pending_gasto", None)
        await q.edit_message_text("Cancelado.")
        return
    if data == "gasto_ok":
        pendientes = context.chat_data.pop("pending_gasto", [])
        if not pendientes:
            await q.edit_message_text("Ya no tengo ese gasto pendiente.")
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
            await q.edit_message_text("✅ Registrado.")
        except Exception:
            logger.exception("Error registrando gasto confirmado")
            await q.edit_message_text("No pude registrarlo.")
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
