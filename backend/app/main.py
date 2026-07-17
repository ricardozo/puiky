"""Punto de entrada de la API de Puiky (FastAPI)."""

from fastapi import FastAPI

from app.routers import notes, projects, tasks

app = FastAPI(
    title="Puiky API",
    description="Asistente personal — backend (Fase 1)",
    version="0.1.0",
)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    """Chequeo de vida del servicio."""
    return {"status": "ok"}


app.include_router(notes.router)
app.include_router(projects.router)
app.include_router(tasks.router)
# Los routers de los demás dominios (finanzas, recordatorios, …) se montan en fases siguientes.
