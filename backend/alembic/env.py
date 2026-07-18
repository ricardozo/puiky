"""Entorno de ejecución de Alembic (multi-schema por inquilino).

Dos cadenas de migración con tablas de versión separadas:

- Control:  `alembic -x control=1 upgrade head`
    → tablas de control (`app_user`, `telegram_link`) en `public`,
      versión en `public.alembic_version_control`.
- Inquilino: `alembic -x tenant=t_<slug> upgrade head`
    → tablas de dominio en el schema `t_<slug>`,
      versión en `<schema>.alembic_version`.

La URL de la BD y la metadata salen de la aplicación (una sola fuente de verdad).
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.config import get_settings
from app.models import Base, ControlBase  # llena ambas metadatas

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _modo() -> tuple[str, str | None]:
    """Devuelve ('control', None) o ('tenant', '<schema>') según -x."""
    x = context.get_x_argument(as_dictionary=True)
    if x.get("tenant"):
        return "tenant", x["tenant"]
    return "control", None


def run_migrations_offline() -> None:
    modo, schema = _modo()
    if modo == "tenant":
        context.configure(
            url=config.get_main_option("sqlalchemy.url"),
            target_metadata=Base.metadata,
            version_table_schema=schema,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
    else:
        context.configure(
            url=config.get_main_option("sqlalchemy.url"),
            target_metadata=ControlBase.metadata,
            version_table="alembic_version_control",
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    modo, schema = _modo()
    # El search_path se fija AL CONECTAR (connect_args), no con un execute suelto:
    # un execute antes de configure abriría una transacción ajena a alembic que
    # terminaría en rollback (nada persistiría).
    search_path = f"{schema},public" if modo == "tenant" else "public"
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"options": f"-c search_path={search_path}"},
    )
    with connectable.connect() as connection:
        if modo == "tenant":
            assert schema is not None
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                version_table_schema=schema,
            )
        else:
            context.configure(
                connection=connection,
                target_metadata=ControlBase.metadata,
                version_table="alembic_version_control",
            )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
