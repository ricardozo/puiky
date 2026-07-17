"""Punto de entrada de la API de Puiky (FastAPI)."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.deps import require_auth
from app.config import get_settings
from app.routers import (
    auth,
    finances,
    nlu,
    notebooks,
    notes,
    projects,
    reminders,
    responsibilities,
    tasks,
)

app = FastAPI(
    title="Puiky API",
    description="Asistente personal — backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    """Chequeo de vida del servicio."""
    return {"status": "ok"}


# Público: login. (/auth/me se protege por su propia dependencia.)
app.include_router(auth.router)

# Todos los dominios requieren autenticación (usuario web o token de servicio).
_protegido = [Depends(require_auth)]
app.include_router(notes.router, dependencies=_protegido)
app.include_router(notebooks.router, dependencies=_protegido)
app.include_router(projects.router, dependencies=_protegido)
app.include_router(tasks.router, dependencies=_protegido)
app.include_router(responsibilities.router, dependencies=_protegido)
app.include_router(finances.accounts_router, dependencies=_protegido)
app.include_router(finances.categories_router, dependencies=_protegido)
app.include_router(finances.transactions_router, dependencies=_protegido)
app.include_router(finances.budgets_router, dependencies=_protegido)
app.include_router(reminders.router, dependencies=_protegido)
app.include_router(nlu.router, dependencies=_protegido)
