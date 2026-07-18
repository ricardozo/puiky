"""Bucle del scheduler (multi-inquilino). Ejecutar:  python -m app.scheduler.main

Cada `SCHEDULER_POLL_SECONDS`, y por CADA inquilino activo: genera avisos
escalonados de vencimientos, crea alertas de presupuesto y entrega los
recordatorios pendientes (con insistencia) por Telegram, al chat de esa persona
(según `public.telegram_link`).
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models.users import TelegramLink, User
from app.scheduler import jobs
from app.scheduler.notifier import Notifier, TelegramNotifier
from app.timeutils import now_local

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("puiky.scheduler")


def _tenants_con_chats(ctrl: Session) -> list[tuple[str, set[int]]]:
    """[(schema, {telegram_ids}), …] de los usuarios activos. Lee control."""
    filas: list[tuple[str, set[int]]] = []
    for u in ctrl.query(User).filter_by(activo=True).all():
        chats = {
            link.telegram_id
            for link in ctrl.query(TelegramLink)
            .filter_by(user_id=u.id, activo=True)
            .all()
        }
        filas.append((u.tenant_schema, chats))
    return filas


async def tick(notifier: Notifier) -> None:
    s = get_settings()
    ahora = now_local()

    with SessionLocal() as ctrl:
        ctrl.execute(text("SET search_path TO public"))
        tenants = _tenants_con_chats(ctrl)

    total_c = total_a = total_e = 0
    for schema, chat_ids in tenants:
        with SessionLocal() as db:
            db.execute(text(f'SET search_path TO "{schema}", public'))
            total_c += jobs.generar_recordatorios_vencimientos(
                db, ahora, s.anticipation_days, s.reminder_hour
            )
            total_a += jobs.generar_alertas_presupuesto(
                db, ahora, s.budget_alert_threshold
            )
            total_e += await jobs.entregar_pendientes(
                db, notifier, chat_ids, ahora, s.reminder_realert_hours
            )

    if total_c or total_a or total_e:
        logger.info(
            "tick: %d avisos, %d alertas de presupuesto, %d entregados (en %d inquilinos)",
            total_c, total_a, total_e, len(tenants),
        )


async def main() -> None:
    s = get_settings()
    if not s.telegram_bot_token:
        raise SystemExit("Falta TELEGRAM_BOT_TOKEN en el entorno.")

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
