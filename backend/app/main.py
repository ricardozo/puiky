"""Punto de entrada de la API de Puiky (FastAPI)."""

from fastapi import FastAPI

from app.routers import (
    finances,
    nlu,
    notes,
    projects,
    reminders,
    responsibilities,
    tasks,
)

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
app.include_router(responsibilities.router)
app.include_router(finances.accounts_router)
app.include_router(finances.categories_router)
app.include_router(finances.transactions_router)
app.include_router(finances.budgets_router)
app.include_router(reminders.router)
app.include_router(nlu.router)
