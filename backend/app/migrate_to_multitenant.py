"""Migración ÚNICA de single-tenant → multi-tenant (schema-per-tenant).

Convierte una BD vieja (todo el dominio en `public`, `app_user` con el esquema
viejo, `alembic_version` en 0011) al modelo nuevo:
- mueve las tablas de dominio de `public` → `t_<slug>`
- deja el control en `public`: `app_user` extendido (+tenant_schema, +activo) y
  `telegram_link`
- sella las tablas de versión (control_0001 en public, domain_0001 en el schema)

Todo en UNA transacción (todo o nada). Uso:

    python -m app.migrate_to_multitenant <slug> [telegram_id]

SIEMPRE con backup previo (pg_dump) y ensayado sobre una copia de la BD real.
"""

import sys

from sqlalchemy import text

from app.database import engine
from app.provision import slug_a_schema

CONTROL_REV = "control_0001"
DOMAIN_REV = "domain_0001"


def migrar(slug: str, telegram_id: int | None) -> str:
    schema = slug_a_schema(slug)  # valida el slug
    with engine.begin() as c:  # transacción única: commit al final, rollback si falla
        # 0) sanity: debe ser una BD vieja aún sin migrar
        cols = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='app_user'"
                )
            )
        }
        if not cols:
            raise SystemExit("No existe public.app_user (¿BD vacía o ya migrada?).")
        if "tenant_schema" in cols:
            raise SystemExit("public.app_user ya tiene tenant_schema: ya migrada.")

        # 1) schema del inquilino
        c.execute(text(f'CREATE SCHEMA "{schema}"'))

        # 2) mover el dominio (todo public menos control y tablas de versión)
        dominio = [
            r[0]
            for r in c.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' AND "
                    "tablename NOT IN ('app_user','telegram_link',"
                    "'alembic_version','alembic_version_control')"
                )
            )
        ]
        for t in dominio:
            c.execute(text(f'ALTER TABLE public."{t}" SET SCHEMA "{schema}"'))

        # 3) versión de dominio en el schema del inquilino
        c.execute(
            text(
                f'CREATE TABLE "{schema}".alembic_version '
                "(version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            )
        )
        c.execute(
            text(f'INSERT INTO "{schema}".alembic_version VALUES (:v)'),
            {"v": DOMAIN_REV},
        )

        # 4) extender app_user a tabla de control
        c.execute(
            text("ALTER TABLE public.app_user ADD COLUMN tenant_schema VARCHAR(63)")
        )
        c.execute(
            text(
                "ALTER TABLE public.app_user "
                "ADD COLUMN activo BOOLEAN NOT NULL DEFAULT true"
            )
        )
        c.execute(
            text("UPDATE public.app_user SET tenant_schema=:s"), {"s": schema}
        )
        c.execute(
            text("ALTER TABLE public.app_user ALTER COLUMN tenant_schema SET NOT NULL")
        )
        c.execute(
            text(
                "ALTER TABLE public.app_user "
                "ADD CONSTRAINT app_user_tenant_schema_key UNIQUE (tenant_schema)"
            )
        )

        # 5) telegram_link
        c.execute(
            text(
                "CREATE TABLE public.telegram_link ("
                " telegram_id BIGINT NOT NULL,"
                " user_id UUID NOT NULL,"
                " activo BOOLEAN NOT NULL DEFAULT true,"
                " creado TIMESTAMPTZ NOT NULL DEFAULT now(),"
                " CONSTRAINT telegram_link_pkey PRIMARY KEY (telegram_id),"
                " CONSTRAINT telegram_link_user_fk FOREIGN KEY (user_id)"
                " REFERENCES public.app_user(id) ON DELETE CASCADE)"
            )
        )
        if telegram_id is not None:
            uid = c.execute(
                text("SELECT id FROM public.app_user WHERE tenant_schema=:s"),
                {"s": schema},
            ).scalar()
            c.execute(
                text(
                    "INSERT INTO public.telegram_link (telegram_id, user_id) "
                    "VALUES (:t, :u)"
                ),
                {"t": telegram_id, "u": uid},
            )

        # 6) versión de control; retirar la vieja de dominio en public
        c.execute(
            text(
                "CREATE TABLE public.alembic_version_control "
                "(version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_control_pkc PRIMARY KEY (version_num))"
            )
        )
        c.execute(
            text("INSERT INTO public.alembic_version_control VALUES (:v)"),
            {"v": CONTROL_REV},
        )
        c.execute(text("DROP TABLE IF EXISTS public.alembic_version"))

    return schema


def main() -> None:
    args = sys.argv[1:]
    if not args:
        raise SystemExit(
            "Uso: python -m app.migrate_to_multitenant <slug> [telegram_id]"
        )
    slug = args[0]
    telegram_id = int(args[1]) if len(args) > 1 else None
    schema = migrar(slug, telegram_id)
    print(f"Migrado a multi-tenant: dominio → {schema}, control en public.")


if __name__ == "__main__":
    main()
