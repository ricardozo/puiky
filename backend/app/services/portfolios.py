"""Lógica de negocio del dominio de portafolios."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.portfolios import Portfolio
from app.models.projects import Project
from app.schemas.portfolios import PortfolioCreate, PortfolioUpdate


def create_portfolio(db: Session, data: PortfolioCreate) -> Portfolio:
    pf = Portfolio(nombre=data.nombre, descripcion=data.descripcion)
    db.add(pf)
    db.commit()
    db.refresh(pf)
    return pf


def get_portfolio(db: Session, portfolio_id: uuid.UUID) -> Portfolio | None:
    return db.get(Portfolio, portfolio_id)


def list_portfolios(db: Session) -> list[tuple[Portfolio, int]]:
    """Portafolios con su conteo de proyectos, ordenados por nombre."""
    conteo = (
        select(Project.portfolio_id, func.count().label("n"))
        .group_by(Project.portfolio_id)
        .subquery()
    )
    stmt = (
        select(Portfolio, func.coalesce(conteo.c.n, 0))
        .join(conteo, conteo.c.portfolio_id == Portfolio.id, isouter=True)
        .order_by(Portfolio.nombre)
    )
    return [(pf, int(n)) for pf, n in db.execute(stmt).all()]


def update_portfolio(
    db: Session, portfolio_id: uuid.UUID, data: PortfolioUpdate
) -> Portfolio | None:
    pf = db.get(Portfolio, portfolio_id)
    if pf is None:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(pf, campo, valor)
    db.commit()
    db.refresh(pf)
    return pf


def delete_portfolio(db: Session, portfolio_id: uuid.UUID) -> bool:
    """Elimina el portafolio; sus proyectos quedan sin portafolio (FK SET NULL)."""
    pf = db.get(Portfolio, portfolio_id)
    if pf is None:
        return False
    db.delete(pf)
    db.commit()
    return True


def count_projects(db: Session, portfolio_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count()).where(Project.portfolio_id == portfolio_id)
    ).scalar_one()
