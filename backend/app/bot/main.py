"""Punto de entrada del bot de Telegram (long-polling).

Ejecutar:  python -m app.bot.main
Requiere TELEGRAM_BOT_TOKEN. Usa long-polling (conexión saliente), así que no
necesita IP pública ni puertos abiertos.
"""

import logging

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot import handlers
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("puiky.bot")


def main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN en el entorno.")
    if not settings.allowed_ids:
        logger.warning(
            "TELEGRAM_ALLOWED_IDS vacío: nadie está autorizado todavía. "
            "Mándale un mensaje al bot y te responderá con tu ID para agregarlo."
        )

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handlers.voz))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.texto))

    logger.info("Bot de Puiky iniciado (long-polling).")
    app.run_polling()


if __name__ == "__main__":
    main()
