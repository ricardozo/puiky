"""Tareas del scheduler: generar recordatorios de vencimientos, alertas de
presupuesto, y entregar los recordatorios pendientes con insistencia.

Todas reciben `ahora` (datetime con zona) como parámetro, para poder testear
con un instante fijo. La generación es idempotente (no duplica).
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finances import Budget, Category
from app.models.reminders import Reminder
from app.models.responsibilities import Responsibility
from app.models.tasks import Task
from app.scheduler.notifier import Notifier
from app.services import market as market_svc
from app.services.finances import _gasto_del_mes, _rango_mes
from app.timeutils import zona


def _cuando(dias: int) -> str:
    if dias <= 0:
        return "hoy"
    if dias == 1:
        return "mañana"
    return f"en {dias} días"


def _existe_reminder(
    db: Session, tipo: str, origen_id, disparar_en: datetime
) -> bool:
    return (
        db.execute(
            select(Reminder.id).where(
                Reminder.origen_tipo == tipo,
                Reminder.origen_id == origen_id,
                Reminder.disparar_en == disparar_en,
            )
        ).first()
        is not None
    )


def _generar_para(
    db: Session,
    tipo: str,
    origen_id,
    etiqueta: str,
    nombre: str,
    fecha_venc,
    ahora: datetime,
    dias_anticipacion: list[int],
    hora_aviso: int,
) -> int:
    """Crea los avisos escalonados futuros para una entidad con vencimiento."""
    creados = 0
    tz = zona()
    for dias in dias_anticipacion:
        fecha_aviso = fecha_venc - timedelta(days=dias)
        disparar_en = datetime.combine(fecha_aviso, time(hora_aviso), tzinfo=tz)
        if disparar_en < ahora:
            continue  # etapa ya pasada
        if _existe_reminder(db, tipo, origen_id, disparar_en):
            continue
        db.add(
            Reminder(
                origen_tipo=tipo,
                origen_id=origen_id,
                texto=f"⏰ {etiqueta} «{nombre}» vence {_cuando(dias)}.",
                disparar_en=disparar_en,
            )
        )
        creados += 1
    return creados


def generar_recordatorios_vencimientos(
    db: Session,
    ahora: datetime,
    dias_anticipacion: list[int],
    hora_aviso: int,
) -> int:
    """Avisos escalonados para tareas (con fecha límite, sin terminar) y
    responsabilidades (por su próximo vencimiento)."""
    creados = 0

    tareas = db.execute(
        select(Task).where(
            Task.fecha_limite.is_not(None), Task.estado != "terminada"
        )
    ).scalars()
    for t in tareas:
        creados += _generar_para(
            db, "task", t.id, "La tarea", t.titulo, t.fecha_limite,
            ahora, dias_anticipacion, hora_aviso,
        )

    resps = db.execute(select(Responsibility)).scalars()
    for r in resps:
        creados += _generar_para(
            db, "responsibility", r.id, "La responsabilidad", r.nombre,
            r.proximo_venc, ahora, dias_anticipacion, hora_aviso,
        )

    if creados:
        db.commit()
    return creados


def _plata(v) -> str:
    return f"${v:,.0f}".replace(",", ".")


def generar_alertas_presupuesto(
    db: Session, ahora: datetime, umbral: float
) -> int:
    """Crea una alerta (recordatorio) por cada presupuesto que cruce el umbral
    del mes. Si el gasto vuelve a quedar bajo el umbral (p. ej. se corrigió un
    movimiento), la alerta pendiente se auto-resuelve; si sigue arriba pero las
    cifras cambiaron, el texto se actualiza (la insistencia repite el texto)."""
    creados = 0
    cambios = False
    inicio, fin = _rango_mes(ahora.year, ahora.month)
    for b in db.execute(select(Budget)).scalars():
        gastado = _gasto_del_mes(db, b.category_id, inicio, fin)
        alerta = db.execute(
            select(Reminder).where(
                Reminder.origen_tipo == "budget",
                Reminder.origen_id == b.id,
                Reminder.resuelto.is_(False),
            )
        ).scalars().first()

        if gastado < Decimal(str(umbral)) * b.tope:
            if alerta is not None:  # ya no aplica: se corrigió el gasto
                alerta.resuelto = True
                cambios = True
            continue

        if b.category_id is not None:
            cat = db.get(Category, b.category_id)
            ambito = f"en {cat.nombre}" if cat else "por categoría"
        else:
            ambito = "global del mes"
        pct = int(gastado / b.tope * 100) if b.tope else 0
        texto = (
            f"⚠️ Presupuesto {ambito}: llevas {_plata(gastado)} de "
            f"{_plata(b.tope)} ({pct}%) este mes."
        )

        if alerta is not None:
            if alerta.texto != texto:  # cifras al día para el próximo aviso
                alerta.texto = texto
                cambios = True
            continue

        db.add(
            Reminder(
                origen_tipo="budget",
                origen_id=b.id,
                texto=texto,
                disparar_en=ahora,
            )
        )
        creados += 1
    if creados or cambios:
        db.commit()
    return creados


def generar_alertas_mercado(db: Session, ahora: datetime) -> int:
    """Crea un aviso por cada producto de mercado que ya toca reponer y que no
    tenga ya una alerta sin resolver. Se auto-resuelve al registrar la compra."""
    creados = 0
    for p in market_svc.por_comprar(db):
        ya = db.execute(
            select(Reminder.id).where(
                Reminder.origen_tipo == "market",
                Reminder.origen_id == p.id,
                Reminder.resuelto.is_(False),
            )
        ).first()
        if ya is not None:
            continue
        dias = p.dias_desde  # type: ignore[attr-defined]
        cadencia = f"cada {p.cadencia_dias} días" if p.cadencia_dias else ""
        cuando = (
            f" (el último fue hace {dias} días)"
            if dias is not None
            else " (aún sin compras registradas)"
        )
        db.add(
            Reminder(
                origen_tipo="market",
                origen_id=p.id,
                texto=f"🛒 Toca reponer «{p.nombre}» — sueles comprarlo {cadencia}{cuando}.",
                disparar_en=ahora,
            )
        )
        creados += 1
    if creados:
        db.commit()
    return creados


async def entregar_pendientes(
    db: Session,
    notifier: Notifier,
    chat_ids: set[int],
    ahora: datetime,
    realert_hours: int,
) -> int:
    """Envía los recordatorios cuyo disparo efectivo ya llegó y aún no están
    resueltos. Insistencia: tras avisar, reprograma el próximo aviso en
    `realert_hours` (via pospuesto_para) para que vuelva hasta que se resuelva."""
    if not chat_ids:
        return 0
    # Cadencia del bot: respeta el snooze del usuario (pospuesto_para) y su propia
    # marca de re-aviso (proximo_aviso), sin pisar una con la otra.
    efectivo = func.coalesce(
        Reminder.proximo_aviso, Reminder.pospuesto_para, Reminder.disparar_en
    )
    due = db.execute(
        select(Reminder)
        .where(Reminder.resuelto.is_(False), efectivo <= ahora)
        .order_by(efectivo)
    ).scalars().all()

    for r in due:
        for chat_id in chat_ids:
            await notifier.send(chat_id, r.texto)
        r.veces_avisado += 1
        r.proximo_aviso = ahora + timedelta(hours=realert_hours)
    if due:
        db.commit()
    return len(due)
