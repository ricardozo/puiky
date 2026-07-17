"""Configuración de la aplicación, leída del entorno (.env).

Nada de rutas, hosts, credenciales ni URLs quemadas en el código: todo
se lee de variables de entorno para que el mismo código corra igual en
Windows (desarrollo) y en Ubuntu (producción).
"""

from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Postgres ---
    postgres_user: str = "puiky"
    postgres_password: str = "puiky"
    postgres_db: str = "puiky"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # --- Embeddings ---
    embedding_model: str = "intfloat/multilingual-e5-base"
    embedding_dim: int = 768

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """URL de conexión SQLAlchemy (driver psycopg 3)."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
