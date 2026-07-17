"""Punto de entrada de la API de Puiky (FastAPI)."""

from fastapi import FastAPI

app = FastAPI(
    title="Puiky API",
    description="Asistente personal — backend (Fase 1)",
    version="0.1.0",
)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    """Chequeo de vida del servicio."""
    return {"status": "ok"}


# Los routers de cada dominio (notas, tareas, …) se montan en pasos siguientes.
