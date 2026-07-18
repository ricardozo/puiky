"""Endpoints HTTP del dominio de portafolios."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.tenancy import get_tenant_db as get_db
from app.schemas.portfolios import (
    PortfolioCreate,
    PortfolioOut,
    PortfolioUpdate,
)
from app.services import portfolios as service

router = APIRouter(prefix="/portfolios", tags=["portafolios"])


def _out(pf, proyectos: int) -> PortfolioOut:
    return PortfolioOut(
        id=pf.id,
        nombre=pf.nombre,
        descripcion=pf.descripcion,
        creada=pf.creada,
        proyectos=proyectos,
    )


@router.post("", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
def crear_portafolio(
    data: PortfolioCreate, db: Session = Depends(get_db)
) -> PortfolioOut:
    return _out(service.create_portfolio(db, data), 0)


@router.get("", response_model=list[PortfolioOut])
def listar_portafolios(db: Session = Depends(get_db)) -> list[PortfolioOut]:
    """Portafolios con su conteo de proyectos."""
    return [_out(pf, n) for pf, n in service.list_portfolios(db)]


@router.get("/{portfolio_id}", response_model=PortfolioOut)
def ver_portafolio(
    portfolio_id: uuid.UUID, db: Session = Depends(get_db)
) -> PortfolioOut:
    pf = service.get_portfolio(db, portfolio_id)
    if pf is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Portafolio no encontrado")
    return _out(pf, service.count_projects(db, portfolio_id))


@router.put("/{portfolio_id}", response_model=PortfolioOut)
def editar_portafolio(
    portfolio_id: uuid.UUID, data: PortfolioUpdate, db: Session = Depends(get_db)
) -> PortfolioOut:
    pf = service.update_portfolio(db, portfolio_id, data)
    if pf is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Portafolio no encontrado")
    return _out(pf, service.count_projects(db, portfolio_id))


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_portafolio(
    portfolio_id: uuid.UUID, db: Session = Depends(get_db)
) -> None:
    """Elimina el portafolio; sus proyectos quedan sin portafolio."""
    if not service.delete_portfolio(db, portfolio_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Portafolio no encontrado")
