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
    # Backend de embeddings: "real" (sentence-transformers) o "fake"
    # (vector determinista sin torch, para tests/CI y arranque rápido).
    embed_backend: str = "real"

    # --- NLU / LLM (tool calling) ---
    # "real" (endpoint OpenAI-compatible, p. ej. Ollama con Qwen) o "fake"
    # (intérprete determinista por reglas, para desarrollo y tests sin modelo).
    llm_backend: str = "fake"
    llm_base_url: str = "http://localhost:11434/v1"  # Ollama por defecto
    llm_model: str = "qwen3:14b"
    llm_api_key: str = "ollama"  # Ollama ignora la clave; el SDK la exige
    # Desactiva el "modo pensamiento" de Qwen3 (razonamiento largo e invisible
    # antes de cada respuesta): mucho más rápido. Poner false para revertir.
    llm_no_think: bool = True
    # Ventana de contexto por petición. El default de Ollama (4096) trunca
    # nuestro prompt (~7k tokens con todas las tools) y degrada al modelo.
    llm_num_ctx: int = 12288

    # --- Transcripción (Whisper) ---
    # "real" (faster-whisper) o "fake" (texto fijo, para probar el flujo).
    whisper_backend: str = "fake"
    whisper_model: str = "base"

    # --- Canal Telegram (Fase 3) ---
    telegram_bot_token: str = ""
    # IDs de Telegram autorizados, separados por coma (allowlist del bot).
    telegram_allowed_ids: str = ""
    # URL de la API de Puiky vista desde el contenedor del bot.
    puiky_api_url: str = "http://app:8000"

    # WhatsApp Cloud API (canal opcional; vacío = deshabilitado)
    wa_access_token: str = ""
    wa_phone_number_id: str = ""
    wa_verify_token: str = ""  # el que se configura en el webhook de Meta

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_ids(self) -> set[int]:
        return {
            int(x) for x in self.telegram_allowed_ids.split(",") if x.strip().isdigit()
        }

    # --- Autenticación (Fase 5) ---
    # Secreto para firmar los JWT de sesión (cámbialo en .env).
    jwt_secret: str = "cambia-este-secreto"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 días
    # Token de servicio para llamantes internos de confianza (el bot). Se envía
    # como Bearer y evita usar el login humano. Distinto del token de sesión.
    service_token: str = ""
    # Orígenes permitidos para CORS (el dev server de Vite), separados por coma.
    cors_origins: str = "http://localhost:5173"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # --- Zona horaria (Fase 4) ---
    timezone: str = "America/Bogota"

    # --- Scheduler (Fase 4) ---
    scheduler_poll_seconds: int = 60
    # Horario de silencio del bot: no se ENVÍAN avisos entre estas horas
    # (los pendientes no se pierden; salen al terminar el silencio).
    notif_silencio_desde: int = 21  # 9 pm
    notif_silencio_hasta: int = 7   # 7 am
    # Insistencia: cada cuántas horas se reitera un recordatorio sin resolver.
    reminder_realert_hours: int = 3
    # Anticipación escalonada (días antes del vencimiento), separada por coma.
    reminder_anticipation_days: str = "3,1,0"
    # Hora local a la que se disparan los avisos de vencimiento.
    reminder_hour: int = 9
    # Umbral de alerta de presupuesto (0.9 = 90% del tope).
    budget_alert_threshold: float = 0.9

    @computed_field  # type: ignore[prop-decorator]
    @property
    def anticipation_days(self) -> list[int]:
        dias = {
            int(x) for x in self.reminder_anticipation_days.split(",") if x.strip().isdigit()
        }
        return sorted(dias, reverse=True)

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
