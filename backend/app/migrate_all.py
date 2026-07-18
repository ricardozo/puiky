"""Migra todo en el deploy: control (public) + dominio de cada inquilino.

Idempotente. Lo usa el servicio `migrate` del compose de producción:
    python -m app.migrate_all

En un deploy nuevo: crea el control y (sin inquilinos aún) termina. Tras la
migración de datos, migra el dominio de cada `app_user` activo a head.
"""

from sqlalchemy import text

from app.database import SessionLocal
from app.provision import upgrade_control, upgrade_tenant

# Se usa print (no logging): alembic llama fileConfig, que desactiva los loggers
# existentes tras la primera migración y silenciaría los mensajes siguientes.


def main() -> None:
    print("[migrate] control (public)…", flush=True)
    upgrade_control()

    with SessionLocal() as db:
        db.execute(text("SET search_path TO public"))
        schemas = [
            row[0]
            for row in db.execute(
                text("SELECT tenant_schema FROM public.app_user WHERE activo")
            ).all()
        ]

    for schema in schemas:
        print(f"[migrate] inquilino {schema}…", flush=True)
        upgrade_tenant(schema)

    print(f"[migrate] completa: control + {len(schemas)} inquilino(s).", flush=True)


if __name__ == "__main__":
    main()
