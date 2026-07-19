"""Regenera el código de vinculación de Telegram de un usuario.

Uso:  python -m app.enroll_code <usuario>

La persona lo usa escribiéndole al bot:  /vincular <código>
"""

import sys

from app.provision import generar_codigo


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: python -m app.enroll_code <usuario>")
    usuario = sys.argv[1]
    codigo = generar_codigo(usuario)
    print(f"Código de vinculación de '{usuario}': {codigo}")
    print("La persona le escribe al bot:  /vincular " + codigo)


if __name__ == "__main__":
    main()
