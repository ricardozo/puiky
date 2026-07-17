"""Bucle del scheduler. Ejecutar:  python -m app.scheduler.main

Cada `SCHEDULER_POLL_SECONDS`: genera avisos escalonados de vencimientos,
crea alertas de presupuesto y entrega los recordatorios pendientes (con
insistencia) por Telegram.
"""

import asyncio
import logging

from app.config import get_settings
from app.database import SessionLocal
from app.scheduler import jobs
from app.scheduler.notifier import Notifier, TelegramNotifier
from app.timeutils import now_local

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("puiky.scheduler")


async def tick(notifier: Notifier) -> None:
    s = get_settings()
    ahora = now_local()
    with SessionLocal() as db:
        creados = jobs.generar_recordatorios_vencimientos(
            db, ahora, s.anticipation_days, s.reminder_hour
        )
        alertas = jobs.generar_alertas_presupuesto(db, ahora, s.budget_alert_threshold)
        enviados = await jobs.entregar_pendientes(
            db, notifier, s.allowed_ids, ahora, s.reminder_realert_hours
        )
    if creados or alertas or enviados:
        logger.info(
            "tick: %d avisos generados, %d alertas de presupuesto, %d entregados",
            creados, alertas, enviados,
        )


async def main() -> None:
    s = get_settings()
    if not s.telegram_bot_token:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN en el entorno.")
    if not s.allowed_ids:
        logger.warning("TELEGRAM_ALLOWED_IDS vacío: no hay a quién notificar.")

    notifier = TelegramNotifier(s.telegram_bot_token)
    logger.info(
        "Scheduler de Puiky iniciado (cada %ds, zona %s).",
        s.scheduler_poll_seconds, s.timezone,
    )
    while True:
        try:
            await tick(notifier)
        except Exception:
            logger.exception("Error en el tick del scheduler")
        await asyncio.sleep(s.scheduler_poll_seconds)


if __name__ == "__main__":
    asyncio.run(main())
