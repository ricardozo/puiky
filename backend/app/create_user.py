"""Crea o actualiza el usuario de la interfaz web (no hay registro público).

Uso:  python -m app.create_user <usuario> <password>
"""

import sys

from sqlalchemy import select

from app.auth.security import hash_password
from app.database import SessionLocal
from app.models.users import User


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Uso: python -m app.create_user <usuario> <password>")
    usuario, password = sys.argv[1], sys.argv[2]
    with SessionLocal() as db:
        user = db.execute(
            select(User).where(User.usuario == usuario)
        ).scalar_one_or_none()
        if user is None:
            db.add(User(usuario=usuario, password_hash=hash_password(password)))
            accion = "creado"
        else:
            user.password_hash = hash_password(password)
            accion = "actualizado"
        db.commit()
    print(f"Usuario '{usuario}' {accion}.")


if __name__ == "__main__":
    main()
