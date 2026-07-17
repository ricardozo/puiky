"""Envío de notificaciones. Real (Telegram) y colector (para tests/dev)."""

from __future__ import annotations

from typing import Protocol


class Notifier(Protocol):
    async def send(self, chat_id: int, texto: str) -> None: ...


class TelegramNotifier:
    """Envía por Telegram con el token del bot. `sendMessage` no choca con el
    `getUpdates` del bot: pueden correr a la vez con el mismo token."""

    def __init__(self, token: str) -> None:
        from telegram import Bot

        self._bot = Bot(token)

    async def send(self, chat_id: int, texto: str) -> None:
        await self._bot.send_message(chat_id=chat_id, text=texto)


class CollectorNotifier:
    """No envía nada; acumula los mensajes. Para verificar sin Telegram."""

    def __init__(self) -> None:
        self.enviados: list[tuple[int, str]] = []

    async def send(self, chat_id: int, texto: str) -> None:
        self.enviados.append((chat_id, texto))
