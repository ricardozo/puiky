"""Enlaza un ID de Telegram a un usuario (para que el bot lo reconozca).

Uso:  python -m app.link_telegram <usuario> <telegram_id>
"""

import sys

from app.provision import link_telegram


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Uso: python -m app.link_telegram <usuario> <telegram_id>")
    usuario, telegram_id = sys.argv[1], sys.argv[2]
    link_telegram(usuario, int(telegram_id))
    print(f"Telegram {telegram_id} enlazado a '{usuario}'.")


if __name__ == "__main__":
    main()
