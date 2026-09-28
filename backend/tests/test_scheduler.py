"""Tests del scheduler que no requieren BD ni Telegram."""

from app.config import Settings
from datetime import date

from app.services.reminders import texto_vencimiento


def test_texto_vencimiento_relativo_a_hoy() -> None:
    hoy = date(2026, 9, 28)
    t = lambda venc: texto_vencimiento("La tarea", "X", venc, hoy)  # noqa: E731
    assert t(date(2026, 9, 28)) == "⏰ La tarea «X» vence hoy."
    assert t(date(2026, 9, 29)) == "⏰ La tarea «X» vence mañana."
    assert t(date(2026, 10, 1)) == "⏰ La tarea «X» vence en 3 días."
    assert t(date(2026, 9, 27)) == "⏰ La tarea «X» venció ayer."
    assert t(date(2026, 9, 22)) == "⏰ La tarea «X» venció hace 6 días."


def test_anticipation_days_parse() -> None:
    assert Settings(reminder_anticipation_days="3,1,0").anticipation_days == [3, 1, 0]
    # ordena desc y descarta no numéricos
    assert Settings(reminder_anticipation_days="1, 5, x, 3").anticipation_days == [5, 3, 1]
