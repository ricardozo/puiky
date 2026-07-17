"""Lógica de negocio del dominio de finanzas.

Reglas de integridad del dinero:
- gasto:        resta `monto` al saldo de la cuenta.
- ingreso:      suma `monto` al saldo de la cuenta.
- transferencia: mueve `monto` de la cuenta origen a la cuenta destino.
Al eliminar un movimiento se revierte su efecto sobre los saldos.

Los errores de validación (cuenta inexistente, transferencia mal formada, etc.)
se señalan con ValueError y el router los traduce a 400.
"""

import calendar
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finances import Account, Budget, Category, Transaction
from app.schemas.finances import (
    AccountCreate,
    AccountUpdate,
    BudgetCreate,
    BudgetUpdate,
    CategoryCreate,
    CategoryUpdate,
    TransactionCreate,
)

GASTO = "gasto"
INGRESO = "ingreso"
TRANSFERENCIA = "transferencia"


# --- Cuentas ---


def create_account(db: Session, data: AccountCreate) -> Account:
    account = Account(nombre=data.nombre, tipo=data.tipo, saldo=data.saldo_inicial)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def get_account(db: Session, account_id: uuid.UUID) -> Account | None:
    return db.get(Account, account_id)


def list_accounts(db: Session) -> list[Account]:
    return list(db.execute(select(Account).order_by(Account.nombre)).scalars().all())


def update_account(
    db: Session, account_id: uuid.UUID, data: AccountUpdate
) -> Account | None:
    account = db.get(Account, account_id)
    if account is None:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(account, campo, valor)
    db.commit()
    db.refresh(account)
    return account


# --- Categorías ---


def create_category(db: Session, data: CategoryCreate) -> Category:
    if db.execute(
        select(Category).where(func.lower(Category.nombre) == data.nombre.lower())
    ).scalar_one_or_none():
        raise ValueError("Ya existe una categoría con ese nombre")
    category = Category(nombre=data.nombre, activa=data.activa)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def list_categories(db: Session, solo_activas: bool = False) -> list[Category]:
    stmt = select(Category)
    if solo_activas:
        stmt = stmt.where(Category.activa.is_(True))
    return list(db.execute(stmt.order_by(Category.nombre)).scalars().all())


def update_category(
    db: Session, category_id: uuid.UUID, data: CategoryUpdate
) -> Category | None:
    category = db.get(Category, category_id)
    if category is None:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(category, campo, valor)
    db.commit()
    db.refresh(category)
    return category


# --- Movimientos ---


def _mover_saldos(
    tipo: str,
    monto: Decimal,
    origen: Account,
    destino: Account | None,
    signo: int,
) -> None:
    """Aplica (signo=+1) o revierte (signo=-1) el efecto en los saldos."""
    delta = monto * signo
    if tipo == GASTO:
        origen.saldo -= delta
    elif tipo == INGRESO:
        origen.saldo += delta
    elif tipo == TRANSFERENCIA:
        origen.saldo -= delta
        assert destino is not None
        destino.saldo += delta


def create_transaction(db: Session, data: TransactionCreate) -> Transaction:
    origen = db.get(Account, data.account_id)
    if origen is None:
        raise ValueError("La cuenta de origen no existe")

    destino: Account | None = None
    tipo = data.tipo.value

    if tipo == TRANSFERENCIA:
        if data.cuenta_destino_id is None:
            raise ValueError("Una transferencia requiere cuenta de destino")
        if data.cuenta_destino_id == data.account_id:
            raise ValueError("La cuenta de destino debe ser distinta de la de origen")
        if data.category_id is not None:
            raise ValueError("Una transferencia no lleva categoría")
        destino = db.get(Account, data.cuenta_destino_id)
        if destino is None:
            raise ValueError("La cuenta de destino no existe")
    else:  # gasto / ingreso
        if data.cuenta_destino_id is not None:
            raise ValueError("Solo las transferencias llevan cuenta de destino")
        if data.category_id is None:
            raise ValueError("Un gasto o ingreso requiere categoría")
        if db.get(Category, data.category_id) is None:
            raise ValueError("La categoría no existe")

    tx = Transaction(
        tipo=tipo,
        monto=data.monto,
        account_id=data.account_id,
        cuenta_destino_id=data.cuenta_destino_id,
        category_id=data.category_id,
        fecha=data.fecha or date.today(),
        nota=data.nota,
    )
    _mover_saldos(tipo, data.monto, origen, destino, signo=1)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def get_transaction(db: Session, tx_id: uuid.UUID) -> Transaction | None:
    return db.get(Transaction, tx_id)


def list_transactions(
    db: Session,
    account_id: uuid.UUID | None = None,
    tipo: str | None = None,
    category_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[Transaction]:
    stmt = select(Transaction)
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)
    if tipo is not None:
        stmt = stmt.where(Transaction.tipo == tipo)
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if desde is not None:
        stmt = stmt.where(Transaction.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(Transaction.fecha <= hasta)
    stmt = stmt.order_by(Transaction.fecha.desc())
    return list(db.execute(stmt).scalars().all())


def delete_transaction(db: Session, tx_id: uuid.UUID) -> bool:
    """Elimina un movimiento y revierte su efecto sobre los saldos."""
    tx = db.get(Transaction, tx_id)
    if tx is None:
        return False
    origen = db.get(Account, tx.account_id)
    destino = (
        db.get(Account, tx.cuenta_destino_id)
        if tx.cuenta_destino_id is not None
        else None
    )
    if origen is not None:
        _mover_saldos(tx.tipo, tx.monto, origen, destino, signo=-1)
    db.delete(tx)
    db.commit()
    return True


# --- Reportes y presupuestos ---


def _rango_mes(anio: int, mes: int) -> tuple[date, date]:
    ultimo = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, 1), date(anio, mes, ultimo)


def reporte_mensual(
    db: Session, anio: int, mes: int
) -> tuple[Decimal, list[tuple[uuid.UUID | None, str, Decimal]]]:
    """Total de gastos del mes y desglose por categoría.

    Solo cuenta `tipo=gasto` (las transferencias no son gasto real)."""
    inicio, fin = _rango_mes(anio, mes)
    stmt = (
        select(
            Transaction.category_id,
            func.coalesce(Category.nombre, "(sin categoría)"),
            func.sum(Transaction.monto),
        )
        .join(Category, Category.id == Transaction.category_id, isouter=True)
        .where(
            Transaction.tipo == GASTO,
            Transaction.fecha >= inicio,
            Transaction.fecha <= fin,
        )
        .group_by(Transaction.category_id, Category.nombre)
        .order_by(func.sum(Transaction.monto).desc())
    )
    filas = db.execute(stmt).all()
    por_categoria = [(cid, nombre, total) for cid, nombre, total in filas]
    total = sum((t for _, _, t in por_categoria), Decimal("0"))
    return total, por_categoria


def _gasto_del_mes(
    db: Session, category_id: uuid.UUID | None, inicio: date, fin: date
) -> Decimal:
    stmt = select(func.coalesce(func.sum(Transaction.monto), 0)).where(
        Transaction.tipo == GASTO,
        Transaction.fecha >= inicio,
        Transaction.fecha <= fin,
    )
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    return Decimal(db.execute(stmt).scalar_one())


def create_budget(db: Session, data: BudgetCreate) -> Budget:
    if data.category_id is not None and db.get(Category, data.category_id) is None:
        raise ValueError("La categoría no existe")
    budget = Budget(
        category_id=data.category_id, tope=data.tope, periodo=data.periodo
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def get_budget(db: Session, budget_id: uuid.UUID) -> Budget | None:
    return db.get(Budget, budget_id)


def list_budgets(db: Session) -> list[Budget]:
    return list(db.execute(select(Budget)).scalars().all())


def update_budget(
    db: Session, budget_id: uuid.UUID, data: BudgetUpdate
) -> Budget | None:
    budget = db.get(Budget, budget_id)
    if budget is None:
        return None
    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(budget, campo, valor)
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, budget_id: uuid.UUID) -> bool:
    budget = db.get(Budget, budget_id)
    if budget is None:
        return False
    db.delete(budget)
    db.commit()
    return True


def budget_progress(
    db: Session, budget_id: uuid.UUID, anio: int, mes: int
) -> tuple[Budget, Decimal] | None:
    """Devuelve (presupuesto, gastado_en_el_mes). Restante y % los arma el
    router. Un presupuesto sin categoría suma todos los gastos del mes."""
    budget = db.get(Budget, budget_id)
    if budget is None:
        return None
    inicio, fin = _rango_mes(anio, mes)
    gastado = _gasto_del_mes(db, budget.category_id, inicio, fin)
    return budget, gastado
