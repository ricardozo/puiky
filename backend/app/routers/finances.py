"""Endpoints HTTP del dominio de finanzas.

Cuatro sub-recursos (cuentas, categorías, movimientos, presupuestos) agrupados
en routers separados que main.py monta juntos.
"""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.tenancy import get_tenant_db as get_db
from app.schemas.finances import (
    AccountCreate,
    AccountOut,
    AccountUpdate,
    BudgetCreate,
    BudgetOut,
    BudgetProgress,
    BudgetUpdate,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    GastoPorCategoria,
    ReporteMensual,
    TransactionCreate,
    TransactionOut,
    TransactionTipo,
    TransactionUpdate,
)
from app.services import finances as service

accounts_router = APIRouter(prefix="/accounts", tags=["finanzas · cuentas"])
categories_router = APIRouter(prefix="/categories", tags=["finanzas · categorías"])
transactions_router = APIRouter(prefix="/transactions", tags=["finanzas · movimientos"])
budgets_router = APIRouter(prefix="/budgets", tags=["finanzas · presupuestos"])


# --- Cuentas ---


@accounts_router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def crear_cuenta(data: AccountCreate, db: Session = Depends(get_db)) -> AccountOut:
    return service.create_account(db, data)


@accounts_router.get("", response_model=list[AccountOut])
def listar_cuentas(db: Session = Depends(get_db)) -> list[AccountOut]:
    return service.list_accounts(db)


@accounts_router.get("/{account_id}", response_model=AccountOut)
def ver_cuenta(account_id: uuid.UUID, db: Session = Depends(get_db)) -> AccountOut:
    """Consultar saldo de una cuenta."""
    cuenta = service.get_account(db, account_id)
    if cuenta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
    return cuenta


@accounts_router.put("/{account_id}", response_model=AccountOut)
def editar_cuenta(
    account_id: uuid.UUID, data: AccountUpdate, db: Session = Depends(get_db)
) -> AccountOut:
    cuenta = service.update_account(db, account_id, data)
    if cuenta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cuenta no encontrada")
    return cuenta


# --- Categorías ---


@categories_router.post(
    "", response_model=CategoryOut, status_code=status.HTTP_201_CREATED
)
def crear_categoria(
    data: CategoryCreate, db: Session = Depends(get_db)
) -> CategoryOut:
    try:
        return service.create_category(db, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@categories_router.get("", response_model=list[CategoryOut])
def listar_categorias(
    solo_activas: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[CategoryOut]:
    return service.list_categories(db, solo_activas)


@categories_router.put("/{category_id}", response_model=CategoryOut)
def editar_categoria(
    category_id: uuid.UUID, data: CategoryUpdate, db: Session = Depends(get_db)
) -> CategoryOut:
    """Editar o desactivar una categoría (no se borra, para no romper el histórico)."""
    categoria = service.update_category(db, category_id, data)
    if categoria is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
    return categoria


# --- Movimientos ---


@transactions_router.post(
    "", response_model=TransactionOut, status_code=status.HTTP_201_CREATED
)
def registrar_movimiento(
    data: TransactionCreate, db: Session = Depends(get_db)
) -> TransactionOut:
    """Registrar gasto, ingreso o transferencia (actualiza saldos)."""
    try:
        return service.create_transaction(db, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@transactions_router.get("", response_model=list[TransactionOut])
def listar_movimientos(
    account_id: uuid.UUID | None = Query(default=None),
    tipo: TransactionTipo | None = Query(default=None),
    category_id: uuid.UUID | None = Query(default=None),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[TransactionOut]:
    return service.list_transactions(
        db,
        account_id,
        tipo.value if tipo is not None else None,
        category_id,
        desde,
        hasta,
    )


_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@transactions_router.get("/export.xlsx")
def exportar_movimientos(
    account_id: uuid.UUID | None = Query(default=None),
    tipo: TransactionTipo | None = Query(default=None),
    category_id: uuid.UUID | None = Query(default=None),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Response:
    """Exporta los movimientos filtrados a un archivo Excel (.xlsx).

    Acepta los mismos filtros que el listado; al filtrar por cuenta incluye las
    transferencias en ambos sentidos, para que coincida con la vista de la web."""
    contenido = service.export_transactions_xlsx(
        db,
        account_id,
        tipo.value if tipo is not None else None,
        category_id,
        desde,
        hasta,
    )
    nombre = f"puiky-finanzas-{date.today():%Y-%m-%d}.xlsx"
    return Response(
        content=contenido,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@transactions_router.get("/reporte", response_model=ReporteMensual)
def reporte_mensual(
    anio: int | None = Query(default=None),
    mes: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> ReporteMensual:
    """Gastos del mes y desglose por categoría (excluye transferencias)."""
    hoy = date.today()
    anio = anio or hoy.year
    mes = mes or hoy.month
    total, por_cat = service.reporte_mensual(db, anio, mes)
    return ReporteMensual(
        anio=anio,
        mes=mes,
        total_gastos=total,
        por_categoria=[
            GastoPorCategoria(category_id=cid, categoria=nombre, total=total)
            for cid, nombre, total in por_cat
        ],
    )


@transactions_router.put("/{tx_id}", response_model=TransactionOut)
def editar_movimiento(
    tx_id: uuid.UUID, data: TransactionUpdate, db: Session = Depends(get_db)
) -> TransactionOut:
    """Edita un movimiento (monto, cuenta, categoría, destino, fecha o nota),
    manteniendo los saldos coherentes. No cambia el tipo."""
    try:
        tx = service.update_transaction(db, tx_id, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if tx is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")
    return tx


@transactions_router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_movimiento(tx_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Elimina un movimiento y revierte su efecto sobre los saldos."""
    if not service.delete_transaction(db, tx_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Movimiento no encontrado")


# --- Presupuestos ---


@budgets_router.post("", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def definir_presupuesto(
    data: BudgetCreate, db: Session = Depends(get_db)
) -> BudgetOut:
    try:
        return service.create_budget(db, data)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@budgets_router.get("", response_model=list[BudgetOut])
def listar_presupuestos(db: Session = Depends(get_db)) -> list[BudgetOut]:
    return service.list_budgets(db)


@budgets_router.get("/{budget_id}/progreso", response_model=BudgetProgress)
def avance_presupuesto(
    budget_id: uuid.UUID,
    anio: int | None = Query(default=None),
    mes: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> BudgetProgress:
    """Consultar avance: gastado vs. tope en el mes indicado (por defecto, el actual)."""
    hoy = date.today()
    resultado = service.budget_progress(
        db, budget_id, anio or hoy.year, mes or hoy.month
    )
    if resultado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Presupuesto no encontrado")
    budget, gastado = resultado
    restante = budget.tope - gastado
    porcentaje = float(gastado / budget.tope * 100) if budget.tope else 0.0
    return BudgetProgress(
        id=budget.id,
        category_id=budget.category_id,
        tope=budget.tope,
        periodo=budget.periodo,
        gastado=gastado,
        restante=restante,
        porcentaje=round(porcentaje, 1),
    )


@budgets_router.put("/{budget_id}", response_model=BudgetOut)
def editar_presupuesto(
    budget_id: uuid.UUID, data: BudgetUpdate, db: Session = Depends(get_db)
) -> BudgetOut:
    budget = service.update_budget(db, budget_id, data)
    if budget is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Presupuesto no encontrado")
    return budget


@budgets_router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_presupuesto(budget_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    if not service.delete_budget(db, budget_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Presupuesto no encontrado")
