"""Tests del scheduler que no requieren BD ni Telegram."""

from app.config import Settings
from app.scheduler.jobs import _cuando


def test_cuando() -> None:
    assert _cuando(0) == "hoy"
    assert _cuando(1) == "mañana"
    assert _cuando(3) == "en 3 días"


def test_anticipation_days_parse() -> None:
    assert Settings(reminder_anticipation_days="3,1,0").anticipation_days == [3, 1, 0]
    # ordena desc y descarta no numéricos
    assert Settings(reminder_anticipation_days="1, 5, x, 3").anticipation_days == [5, 3, 1]
