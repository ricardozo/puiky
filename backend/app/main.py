"""Punto de entrada de la API de Puiky (FastAPI)."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.tenancy import get_tenant_db
from app.routers import (
    auth,
    finances,
    nlu,
    notebooks,
    notes,
    portfolios,
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

# Todos los dominios pasan por get_tenant_db: autentica (usuario web o token de
# servicio + X-Tenant-User) y acota la sesión al schema del inquilino. Se monta
# a nivel de router para cubrir también rutas sin `db` (p. ej. transcribir);
# FastAPI cachea la dependencia, así que es una sola sesión por petición.
_protegido = [Depends(get_tenant_db)]
app.include_router(notes.router, dependencies=_protegido)
app.include_router(notebooks.router, dependencies=_protegido)
app.include_router(portfolios.router, dependencies=_protegido)
app.include_router(projects.router, dependencies=_protegido)
app.include_router(tasks.router, dependencies=_protegido)
app.include_router(responsibilities.router, dependencies=_protegido)
app.include_router(finances.accounts_router, dependencies=_protegido)
app.include_router(finances.categories_router, dependencies=_protegido)
app.include_router(finances.transactions_router, dependencies=_protegido)
app.include_router(finances.budgets_router, dependencies=_protegido)
app.include_router(reminders.router, dependencies=_protegido)
app.include_router(nlu.router, dependencies=_protegido)
