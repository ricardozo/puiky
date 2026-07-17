"""Tests del bot que no requieren Telegram vivo: allowlist y parseo de IDs."""

from app.bot.handlers import esta_autorizado
from app.config import Settings


def test_allowlist_decision() -> None:
    assert esta_autorizado(123, {123, 456})
    assert not esta_autorizado(999, {123})
    assert not esta_autorizado(None, {123})
    # Allowlist vacía = nadie autorizado (seguro por defecto).
    assert not esta_autorizado(123, set())


def test_parseo_allowed_ids() -> None:
    s = Settings(telegram_allowed_ids="123, 456 ,abc,")
    assert s.allowed_ids == {123, 456}

    vacia = Settings(telegram_allowed_ids="")
    assert vacia.allowed_ids == set()
