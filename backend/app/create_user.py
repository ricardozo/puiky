"""Crea o actualiza un usuario web y provisiona su inquilino (schema + dominio).

Uso:  python -m app.create_user <usuario> <password> [slug]

Si no se da `slug`, se usa el `usuario` como slug. El schema del inquilino será
`t_<slug>`. Requiere que la cadena de control ya esté aplicada en `public`.
"""

import sys

from app.provision import crear_usuario


def main() -> None:
    args = sys.argv[1:]
    if len(args) not in (2, 3):
        raise SystemExit("Uso: python -m app.create_user <usuario> <password> [slug]")
    usuario, password = args[0], args[1]
    slug = args[2] if len(args) == 3 else usuario
    schema, accion, codigo = crear_usuario(usuario, password, slug)
    print(f"Usuario '{usuario}' {accion} (inquilino {schema}).")
    print(f"Código de vinculación de Telegram: {codigo}")
    print("La persona le escribe al bot:  /vincular " + codigo)


if __name__ == "__main__":
    main()
