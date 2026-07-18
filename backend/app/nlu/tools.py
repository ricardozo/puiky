"""Definición de las herramientas (tools) que el LLM puede invocar.

Cada tool declara su esquema (para el modelo) y un handler que resuelve las
referencias por nombre (el usuario dice "la cuenta de ahorros", no un UUID) y
llama a la capa `services`. Los handlers devuelven dicts serializables que se
le devuelven al modelo para que redacte la confirmación.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finances import Account, Budget, Category, Transaction
from app.models.notebooks import Notebook
from app.models.notes import Note
from app.models.portfolios import Portfolio
from app.models.projects import Project
from app.models.reminders import Reminder
from app.models.responsibilities import Responsibility
from app.models.tasks import Task
from app.schemas.finances import (
    AccountCreate,
    BudgetCreate,
    CategoryCreate,
    TransactionCreate,
    TransactionTipo,
)
from app.schemas.notebooks import NotebookCreate
from app.schemas.notes import NoteCreate, NoteLinkCreate, NoteUpdate
from app.schemas.portfolios import PortfolioCreate
from app.schemas.projects import ProjectCreate, ProjectEstado, ProjectUpdate
from app.schemas.reminders import ReminderCreate
from app.schemas.responsibilities import ResponsibilityCreate, ResponsibilityUpdate
from app.schemas.tasks import (
    ChecklistItemCreate,
    ChecklistItemUpdate,
    TaskCreate,
    TaskEstado,
    TaskUpdate,
)
from app.services import finances as fin
from app.services import notebooks as nb_svc
from app.services import notes as notes_svc
from app.services import portfolios as pf_svc
from app.services import projects as proj_svc
from app.services import reminders as rem_svc
from app.services import responsibilities as resp_svc
from app.services import tasks as task_svc


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[[Session, dict], dict]


# --- Resolución de referencias por nombre ---


def _resolver(db: Session, modelo, columna, ref: str, etiqueta: str):
    ref = (ref or "").strip()
    if not ref:
        raise ValueError(f"Falta indicar {etiqueta}.")
    filas = list(
        db.execute(select(modelo).where(columna.ilike(f"%{ref}%"))).scalars().all()
    )
    if not filas:
        raise ValueError(f"No encontré {etiqueta} que coincida con «{ref}».")
    if len(filas) > 1:
        nombres = ", ".join(getattr(f, columna.key) for f in filas[:5])
        raise ValueError(f"«{ref}» es ambiguo; coinciden: {nombres}.")
    return filas[0]


def _resolver_cuenta(db: Session, ref: str) -> Account:
    return _resolver(db, Account, Account.nombre, ref, "una cuenta")


def _resolver_categoria(db: Session, ref: str) -> Category:
    ref = (ref or "").strip()
    if not ref:
        raise ValueError("Falta indicar la categoría.")
    fila = db.execute(
        select(Category).where(
            func.lower(Category.nombre) == ref.lower(), Category.activa.is_(True)
        )
    ).scalar_one_or_none()
    if fila is None:
        fila = db.execute(
            select(Category).where(
                Category.nombre.ilike(f"%{ref}%"), Category.activa.is_(True)
            )
        ).scalars().first()
    if fila is None:
        raise ValueError(f"No existe la categoría «{ref}».")
    return fila


def _resolver_tarea(db: Session, ref: str) -> Task:
    return _resolver(db, Task, Task.titulo, ref, "una tarea")


def _resolver_proyecto(db: Session, ref: str) -> Project:
    return _resolver(db, Project, Project.nombre, ref, "un proyecto")


def _resolver_cuaderno(db: Session, ref: str) -> Notebook:
    return _resolver(db, Notebook, Notebook.nombre, ref, "un cuaderno")


def _resolver_portafolio(db: Session, ref: str) -> Portfolio:
    return _resolver(db, Portfolio, Portfolio.nombre, ref, "un portafolio")


def _resolver_item(tarea: Task, ref: str):
    """Encuentra un ítem del checklist de la tarea por su texto (ilike)."""
    ref = (ref or "").strip().lower()
    if not ref:
        raise ValueError("Falta indicar el ítem del checklist.")
    coincidencias = [i for i in tarea.checklist if ref in i.texto.lower()]
    if not coincidencias:
        raise ValueError(f"No encontré un ítem que coincida con «{ref}».")
    if len(coincidencias) > 1:
        textos = ", ".join(i.texto for i in coincidencias[:5])
        raise ValueError(f"«{ref}» coincide con varios ítems: {textos}.")
    return coincidencias[0]


def _resolver_hoja(db: Session, ref: str) -> Note | None:
    """Busca una hoja por su título (ilike). None si no existe; error si varias."""
    ref = (ref or "").strip()
    if not ref:
        raise ValueError("Falta indicar la hoja.")
    filas = list(
        db.execute(select(Note).where(Note.titulo.ilike(f"%{ref}%"))).scalars().all()
    )
    if len(filas) == 1:
        return filas[0]
    if len(filas) > 1:
        titulos = ", ".join(f.titulo for f in filas[:5] if f.titulo)
        raise ValueError(f"«{ref}» coincide con varias hojas: {titulos}.")
    return None


def _etiqueta_hoja(n: Note) -> str:
    return n.titulo or n.contenido[:40]


def _money(v: Any) -> str:
    return f"{float(v):.2f}"


# --- Handlers: hojas y cuadernos ---


def _crear_hoja(db: Session, a: dict) -> dict:
    nb_id = _resolver_cuaderno(db, a["cuaderno"]).id if a.get("cuaderno") else None
    nota = notes_svc.create_note(
        db,
        NoteCreate(
            contenido=a["contenido"], titulo=a.get("titulo"), notebook_id=nb_id
        ),
    )
    return {"ok": True, "hoja": _etiqueta_hoja(nota), "cuaderno": a.get("cuaderno")}


def _anadir_a_hoja(db: Session, a: dict) -> dict:
    """Añade texto a una hoja existente (por título); si no existe, la crea."""
    hoja = _resolver_hoja(db, a["hoja"])
    if hoja is None:
        nota = notes_svc.create_note(
            db, NoteCreate(contenido=a["texto"], titulo=a["hoja"])
        )
        return {"ok": True, "creada": True, "hoja": _etiqueta_hoja(nota)}
    notes_svc.append_note(db, hoja.id, a["texto"])
    return {"ok": True, "creada": False, "hoja": _etiqueta_hoja(hoja)}


def _editar_hoja(db: Session, a: dict) -> dict:
    hoja = _resolver_hoja(db, a["hoja"])
    if hoja is None:
        raise ValueError(f"No encontré la hoja «{a['hoja']}».")
    campos: dict[str, Any] = {}
    if a.get("nuevo_titulo") is not None:
        campos["titulo"] = a["nuevo_titulo"]
    if a.get("nuevo_contenido") is not None:
        campos["contenido"] = a["nuevo_contenido"]
    notes_svc.update_note(db, hoja.id, NoteUpdate(**campos))
    return {"ok": True, "hoja": campos.get("titulo") or _etiqueta_hoja(hoja)}


def _mover_hoja(db: Session, a: dict) -> dict:
    hoja = _resolver_hoja(db, a["hoja"])
    if hoja is None:
        raise ValueError(f"No encontré la hoja «{a['hoja']}».")
    nb = _resolver_cuaderno(db, a["cuaderno"])
    notes_svc.update_note(db, hoja.id, NoteUpdate(notebook_id=nb.id))
    return {"ok": True, "hoja": _etiqueta_hoja(hoja), "cuaderno": nb.nombre}


def _eliminar_hoja(db: Session, a: dict) -> dict:
    """No borra: pide confirmación (el bot mostrará botones)."""
    hoja = _resolver_hoja(db, a["hoja"])
    if hoja is None:
        raise ValueError(f"No encontré la hoja «{a['hoja']}».")
    return {
        "ok": True,
        "confirmar": {
            "tipo": "note",
            "id": str(hoja.id),
            "que": f"la hoja «{_etiqueta_hoja(hoja)}»",
        },
    }


def _buscar_hojas(db: Session, a: dict) -> dict:
    res = notes_svc.search_notes(db, a["texto"], int(a.get("limite", 5)))
    return {
        "ok": True,
        "resultados": [
            {"hoja": _etiqueta_hoja(n), "similitud": round(s, 3)} for n, s in res
        ],
    }


def _listar_hojas(db: Session, a: dict) -> dict:
    if a.get("cuaderno"):
        nb = _resolver_cuaderno(db, a["cuaderno"])
        notas = notes_svc.list_notes(db, notebook_id=nb.id)
    else:
        notas = notes_svc.list_notes(db)
    return {"ok": True, "hojas": [_etiqueta_hoja(n) for n in notas]}


def _crear_cuaderno(db: Session, a: dict) -> dict:
    nb = nb_svc.create_notebook(db, NotebookCreate(nombre=a["nombre"]))
    return {"ok": True, "cuaderno": nb.nombre}


def _listar_cuadernos(db: Session, a: dict) -> dict:
    return {
        "ok": True,
        "cuadernos": [
            {"nombre": nb.nombre, "notas": n} for nb, n in nb_svc.list_notebooks(db)
        ],
    }


# --- Handlers: resto ---


def _crear_portafolio(db: Session, a: dict) -> dict:
    pf = pf_svc.create_portfolio(db, PortfolioCreate(nombre=a["nombre"]))
    return {"ok": True, "portafolio": pf.nombre}


def _listar_portafolios(db: Session, a: dict) -> dict:
    return {
        "ok": True,
        "portafolios": [
            {"nombre": pf.nombre, "proyectos": n}
            for pf, n in pf_svc.list_portfolios(db)
        ],
    }


def _eliminar_portafolio(db: Session, a: dict) -> dict:
    pf = _resolver_portafolio(db, a["portafolio"])
    return {
        "ok": True,
        "confirmar": {
            "tipo": "portfolio",
            "id": str(pf.id),
            "que": f"el portafolio «{pf.nombre}» (sus proyectos quedan sueltos)",
        },
    }


def _crear_proyecto(db: Session, a: dict) -> dict:
    pf_id = (
        _resolver_portafolio(db, a["portafolio"]).id if a.get("portafolio") else None
    )
    p = proj_svc.create_project(
        db,
        ProjectCreate(
            nombre=a["nombre"],
            descripcion=a.get("descripcion"),
            portfolio_id=pf_id,
        ),
    )
    return {"ok": True, "proyecto": p.nombre, "portafolio": a.get("portafolio")}


def _listar_proyectos(db: Session, a: dict) -> dict:
    if a.get("portafolio"):
        pf_id = _resolver_portafolio(db, a["portafolio"]).id
        proys = proj_svc.list_projects(db, portfolio_id=pf_id)
    else:
        proys = proj_svc.list_projects(db)
    return {
        "ok": True,
        "proyectos": [{"nombre": p.nombre, "estado": p.estado} for p in proys],
    }


def _ver_proyecto(db: Session, a: dict) -> dict:
    proyecto = _resolver_proyecto(db, a["proyecto"])
    p = proj_svc.get_project(db, proyecto.id)
    notas = notes_svc.notes_for_entity(db, "project", proyecto.id)
    return {
        "ok": True,
        "proyecto": p.nombre,
        "estado": p.estado,
        "tareas": [_resumen_tarea(t) for t in p.tasks],
        "notas": [_etiqueta_hoja(n) for n in notas],
    }


def _mover_proyecto(db: Session, a: dict) -> dict:
    proyecto = _resolver_proyecto(db, a["proyecto"])
    pf = _resolver_portafolio(db, a["portafolio"])
    proj_svc.update_project(db, proyecto.id, ProjectUpdate(portfolio_id=pf.id))
    return {"ok": True, "proyecto": proyecto.nombre, "portafolio": pf.nombre}


def _archivar_proyecto(db: Session, a: dict) -> dict:
    proyecto = _resolver_proyecto(db, a["proyecto"])
    p = proj_svc.archive_project(db, proyecto.id)
    return {"ok": True, "proyecto": p.nombre, "estado": p.estado}


def _editar_proyecto(db: Session, a: dict) -> dict:
    proyecto = _resolver_proyecto(db, a["proyecto"])
    campos: dict[str, Any] = {}
    if a.get("nuevo_nombre"):
        campos["nombre"] = a["nuevo_nombre"]
    if a.get("descripcion") is not None:
        campos["descripcion"] = a["descripcion"]
    if a.get("estado"):
        campos["estado"] = ProjectEstado(a["estado"])
    if not campos:
        raise ValueError("No indicaste qué cambiar del proyecto.")
    p = proj_svc.update_project(db, proyecto.id, ProjectUpdate(**campos))
    return {"ok": True, "proyecto": p.nombre, "estado": p.estado}


def _crear_tarea(db: Session, a: dict) -> dict:
    project_id = None
    if a.get("proyecto"):
        project_id = _resolver_proyecto(db, a["proyecto"]).id
    fecha = date.fromisoformat(a["fecha_limite"]) if a.get("fecha_limite") else None
    t = task_svc.create_task(
        db,
        TaskCreate(titulo=a["titulo"], project_id=project_id, fecha_limite=fecha),
    )
    return {"ok": True, "tarea_id": str(t.id), "titulo": t.titulo}


def _actualizar_avance_tarea(db: Session, a: dict) -> dict:
    tarea = _resolver_tarea(db, a["tarea"])
    t = task_svc.set_progress(db, tarea.id, int(a["avance_pct"]))
    return {"ok": True, "titulo": t.titulo, "avance_pct": t.avance_pct}


def _completar_tarea(db: Session, a: dict) -> dict:
    tarea = _resolver_tarea(db, a["tarea"])
    t = task_svc.complete_task(db, tarea.id)
    return {"ok": True, "titulo": t.titulo, "estado": t.estado}


def _listar_tareas_pendientes(db: Session, a: dict) -> dict:
    return {
        "ok": True,
        "tareas": [_resumen_tarea(t) for t in task_svc.list_pendientes(db)],
    }


def _resumen_tarea(t: Task) -> dict:
    return {
        "titulo": t.titulo,
        "proyecto": t.proyecto,
        "estado": t.estado,
        "avance_pct": t.avance_pct,
    }


_FECHAS_TAREA = [
    "fecha_limite",
    "fecha_inicio_plan",
    "fecha_inicio_real",
    "fecha_fin_real",
]


def _editar_tarea(db: Session, a: dict) -> dict:
    """Edita campos de una tarea (por su título): descripción, notas rápidas,
    estado y fechas. `fecha_limite` es el fin planeado."""
    tarea = _resolver_tarea(db, a["tarea"])
    campos: dict[str, Any] = {}
    if a.get("descripcion") is not None:
        campos["descripcion"] = a["descripcion"]
    if a.get("notas") is not None:
        campos["notas"] = a["notas"]
    if a.get("estado"):
        campos["estado"] = TaskEstado(a["estado"])
    for f in _FECHAS_TAREA:
        if a.get(f):
            campos[f] = date.fromisoformat(a[f])
    if not campos:
        raise ValueError("No indicaste qué cambiar de la tarea.")
    t = task_svc.update_task(db, tarea.id, TaskUpdate(**campos))
    return {"ok": True, **_resumen_tarea(t)}


def _eliminar_tarea(db: Session, a: dict) -> dict:
    tarea = _resolver_tarea(db, a["tarea"])
    return {
        "ok": True,
        "confirmar": {
            "tipo": "task",
            "id": str(tarea.id),
            "que": f"la tarea «{tarea.titulo}»",
        },
    }


def _listar_tareas(db: Session, a: dict) -> dict:
    project_id = _resolver_proyecto(db, a["proyecto"]).id if a.get("proyecto") else None
    tareas = task_svc.list_tasks(db, project_id=project_id)
    return {"ok": True, "tareas": [_resumen_tarea(t) for t in tareas]}


def _tareas_de_hoy(db: Session, a: dict) -> dict:
    return {"ok": True, "tareas": [_resumen_tarea(t) for t in task_svc.list_hoy(db)]}


# --- Checklist de una tarea ---


def _agregar_item_checklist(db: Session, a: dict) -> dict:
    tarea = _resolver_tarea(db, a["tarea"])
    t = task_svc.add_checklist_item(db, tarea.id, ChecklistItemCreate(texto=a["texto"]))
    return {"ok": True, "tarea": t.titulo, "avance_pct": t.avance_pct}


def _marcar_item_checklist(db: Session, a: dict) -> dict:
    tarea = _resolver_tarea(db, a["tarea"])
    t = task_svc.get_task(db, tarea.id)
    item = _resolver_item(t, a["item"])
    hecho = bool(a.get("hecho", True))
    t = task_svc.update_checklist_item(db, item.id, ChecklistItemUpdate(hecho=hecho))
    return {
        "ok": True,
        "item": item.texto,
        "hecho": hecho,
        "tarea": t.titulo,
        "avance_pct": t.avance_pct,
        "estado": t.estado,
    }


def _quitar_item_checklist(db: Session, a: dict) -> dict:
    tarea = _resolver_tarea(db, a["tarea"])
    t = task_svc.get_task(db, tarea.id)
    item = _resolver_item(t, a["item"])
    texto = item.texto  # guardar antes de borrar (el objeto queda inválido)
    t = task_svc.delete_checklist_item(db, item.id)
    return {"ok": True, "quitado": texto, "tarea": t.titulo}


def _agregar_nota_a_tarea(db: Session, a: dict) -> dict:
    """Crea una hoja y la vincula a la tarea (varias notas por tarea)."""
    tarea = _resolver_tarea(db, a["tarea"])
    nota = notes_svc.create_note(
        db, NoteCreate(contenido=a["contenido"], titulo=a.get("titulo"))
    )
    notes_svc.add_link(
        db,
        nota.id,
        NoteLinkCreate(entidad_tipo="task", entidad_id=tarea.id),
    )
    return {"ok": True, "tarea": tarea.titulo, "nota": _etiqueta_hoja(nota)}


def _registrar_movimiento(db: Session, a: dict, tipo: TransactionTipo) -> dict:
    cuenta = _resolver_cuenta(db, a["cuenta"])
    categoria = _resolver_categoria(db, a["categoria"])
    tx = fin.create_transaction(
        db,
        TransactionCreate(
            tipo=tipo,
            monto=a["monto"],
            account_id=cuenta.id,
            category_id=categoria.id,
            nota=a.get("nota"),
        ),
    )
    db.refresh(cuenta)
    return {
        "ok": True,
        "tipo": tx.tipo,
        "monto": _money(tx.monto),
        "cuenta": cuenta.nombre,
        "categoria": categoria.nombre,
        "saldo_cuenta": _money(cuenta.saldo),
    }


def _registrar_gasto(db: Session, a: dict) -> dict:
    return _registrar_movimiento(db, a, TransactionTipo.gasto)


def _registrar_ingreso(db: Session, a: dict) -> dict:
    return _registrar_movimiento(db, a, TransactionTipo.ingreso)


def _transferir(db: Session, a: dict) -> dict:
    origen = _resolver_cuenta(db, a["cuenta_origen"])
    destino = _resolver_cuenta(db, a["cuenta_destino"])
    fin.create_transaction(
        db,
        TransactionCreate(
            tipo=TransactionTipo.transferencia,
            monto=a["monto"],
            account_id=origen.id,
            cuenta_destino_id=destino.id,
        ),
    )
    db.refresh(origen)
    db.refresh(destino)
    return {
        "ok": True,
        "monto": _money(a["monto"]),
        "origen": f"{origen.nombre} ({_money(origen.saldo)})",
        "destino": f"{destino.nombre} ({_money(destino.saldo)})",
    }


def _consultar_saldo(db: Session, a: dict) -> dict:
    cuenta = _resolver_cuenta(db, a["cuenta"])
    return {"ok": True, "cuenta": cuenta.nombre, "saldo": _money(cuenta.saldo)}


def _gastos_del_mes(db: Session, a: dict) -> dict:
    hoy = date.today()
    total, por_cat = fin.reporte_mensual(db, hoy.year, hoy.month)
    return {
        "ok": True,
        "total_gastos": _money(total),
        "por_categoria": [
            {"categoria": nombre, "total": _money(tot)} for _, nombre, tot in por_cat
        ],
    }


def _crear_cuenta(db: Session, a: dict) -> dict:
    acc = fin.create_account(
        db,
        AccountCreate(
            nombre=a["nombre"],
            tipo=a.get("tipo") or "efectivo",
            saldo_inicial=a.get("saldo_inicial") or 0,
        ),
    )
    return {"ok": True, "cuenta": acc.nombre, "saldo": _money(acc.saldo)}


def _listar_cuentas(db: Session, a: dict) -> dict:
    cuentas = fin.list_accounts(db)
    total = sum(float(c.saldo) for c in cuentas)
    return {
        "ok": True,
        "cuentas": [
            {"nombre": c.nombre, "tipo": c.tipo, "saldo": _money(c.saldo)}
            for c in cuentas
        ],
        "total": f"{total:.2f}",
    }


def _crear_categoria(db: Session, a: dict) -> dict:
    c = fin.create_category(db, CategoryCreate(nombre=a["nombre"]))
    return {"ok": True, "categoria": c.nombre}


def _nombre_cuenta(db: Session, id_) -> str:
    c = db.get(Account, id_) if id_ else None
    return c.nombre if c else "—"


def _nombre_categoria(db: Session, id_) -> str:
    c = db.get(Category, id_) if id_ else None
    return c.nombre if c else "—"


def _listar_movimientos(db: Session, a: dict) -> dict:
    acc_id = _resolver_cuenta(db, a["cuenta"]).id if a.get("cuenta") else None
    txs = fin.list_transactions(db, account_id=acc_id)[:15]
    return {
        "ok": True,
        "movimientos": [
            {
                "tipo": t.tipo,
                "monto": _money(t.monto),
                "cuenta": _nombre_cuenta(db, t.account_id),
                "categoria": _nombre_categoria(db, t.category_id),
                "fecha": t.fecha.isoformat(),
            }
            for t in txs
        ],
    }


def _eliminar_ultimo_movimiento(db: Session, a: dict) -> dict:
    tx = db.execute(
        select(Transaction).order_by(Transaction.fecha.desc()).limit(1)
    ).scalar_one_or_none()
    if tx is None:
        raise ValueError("No hay movimientos para eliminar.")
    cuenta = _nombre_cuenta(db, tx.account_id)
    return {
        "ok": True,
        "confirmar": {
            "tipo": "transaction",
            "id": str(tx.id),
            "que": f"el último movimiento ({tx.tipo} de {_money(tx.monto)} en {cuenta})",
        },
    }


def _definir_presupuesto(db: Session, a: dict) -> dict:
    cat_id = _resolver_categoria(db, a["categoria"]).id if a.get("categoria") else None
    b = fin.create_budget(db, BudgetCreate(tope=a["tope"], category_id=cat_id))
    return {
        "ok": True,
        "tope": _money(b.tope),
        "categoria": a.get("categoria") or "global",
    }


def _progreso_budget(db: Session, b: Budget) -> dict:
    hoy = date.today()
    _, gastado = fin.budget_progress(db, b.id, hoy.year, hoy.month)
    pct = round(float(gastado / b.tope * 100)) if b.tope else 0
    return {
        "categoria": _nombre_categoria(db, b.category_id)
        if b.category_id
        else "global",
        "gastado": _money(gastado),
        "tope": _money(b.tope),
        "restante": _money(b.tope - gastado),
        "porcentaje": pct,
    }


def _avance_presupuesto(db: Session, a: dict) -> dict:
    cat_id = _resolver_categoria(db, a["categoria"]).id if a.get("categoria") else None
    budget = db.execute(
        select(Budget).where(Budget.category_id == cat_id)
    ).scalars().first()
    if budget is None:
        cual = "esa categoría" if cat_id else "el mes (global)"
        raise ValueError(f"No hay un presupuesto para {cual}.")
    return {"ok": True, **_progreso_budget(db, budget)}


def _listar_presupuestos(db: Session, a: dict) -> dict:
    return {
        "ok": True,
        "presupuestos": [_progreso_budget(db, b) for b in fin.list_budgets(db)],
    }


def _crear_recordatorio(db: Session, a: dict) -> dict:
    disparar = (
        datetime.fromisoformat(a["disparar_en"])
        if a.get("disparar_en")
        else datetime.now().astimezone()
    )
    r = rem_svc.create_reminder(
        db, ReminderCreate(texto=a["texto"], disparar_en=disparar)
    )
    return {"ok": True, "texto": r.texto, "disparar_en": r.disparar_en.isoformat()}


def _crear_responsabilidad(db: Session, a: dict) -> dict:
    r = resp_svc.create_responsibility(
        db,
        ResponsibilityCreate(
            nombre=a["nombre"],
            recurrencia=a["recurrencia"],
            proximo_venc=date.fromisoformat(a["proximo_venc"]),
            monto=a.get("monto"),
        ),
    )
    return {"ok": True, "nombre": r.nombre, "proximo_venc": r.proximo_venc.isoformat()}


def _resolver_responsabilidad(db: Session, ref: str) -> Responsibility:
    return _resolver(
        db, Responsibility, Responsibility.nombre, ref, "una responsabilidad"
    )


def _resolver_recordatorio(db: Session, ref: str) -> Reminder:
    ref = (ref or "").strip()
    if not ref:
        raise ValueError("Falta indicar el recordatorio.")
    filas = list(
        db.execute(
            select(Reminder).where(
                Reminder.texto.ilike(f"%{ref}%"), Reminder.resuelto.is_(False)
            )
        ).scalars().all()
    )
    if not filas:
        raise ValueError(f"No encontré un recordatorio pendiente con «{ref}».")
    if len(filas) > 1:
        textos = ", ".join(r.texto[:30] for r in filas[:5])
        raise ValueError(f"«{ref}» coincide con varios recordatorios: {textos}.")
    return filas[0]


def _listar_responsabilidades(db: Session, a: dict) -> dict:
    rs = resp_svc.list_responsibilities(db)
    return {
        "ok": True,
        "responsabilidades": [
            {
                "nombre": r.nombre,
                "recurrencia": r.recurrencia,
                "proximo_venc": r.proximo_venc.isoformat(),
                "monto": _money(r.monto) if r.monto is not None else None,
            }
            for r in rs
        ],
    }


def _cumplir_responsabilidad(db: Session, a: dict) -> dict:
    r = _resolver_responsabilidad(db, a["responsabilidad"])
    r2 = resp_svc.fulfill_responsibility(db, r.id)
    return {
        "ok": True,
        "responsabilidad": r2.nombre,
        "proximo_venc": r2.proximo_venc.isoformat(),
    }


def _editar_responsabilidad(db: Session, a: dict) -> dict:
    r = _resolver_responsabilidad(db, a["responsabilidad"])
    campos: dict[str, Any] = {}
    if a.get("nuevo_nombre"):
        campos["nombre"] = a["nuevo_nombre"]
    if a.get("recurrencia"):
        campos["recurrencia"] = a["recurrencia"]
    if a.get("proximo_venc"):
        campos["proximo_venc"] = date.fromisoformat(a["proximo_venc"])
    if a.get("monto") is not None:
        campos["monto"] = a["monto"]
    if not campos:
        raise ValueError("No indicaste qué cambiar de la responsabilidad.")
    r2 = resp_svc.update_responsibility(db, r.id, ResponsibilityUpdate(**campos))
    return {"ok": True, "responsabilidad": r2.nombre}


def _eliminar_responsabilidad(db: Session, a: dict) -> dict:
    r = _resolver_responsabilidad(db, a["responsabilidad"])
    return {
        "ok": True,
        "confirmar": {
            "tipo": "responsibility",
            "id": str(r.id),
            "que": f"la responsabilidad «{r.nombre}»",
        },
    }


def _listar_recordatorios(db: Session, a: dict) -> dict:
    rs = rem_svc.list_reminders(db, resuelto=False)
    return {
        "ok": True,
        "recordatorios": [
            {
                "texto": r.texto,
                "cuando": (r.pospuesto_para or r.disparar_en).isoformat(),
                "avisos": r.veces_avisado,
            }
            for r in rs
        ],
    }


def _recordatorios_vencidos(db: Session, a: dict) -> dict:
    return {"ok": True, "recordatorios": [r.texto for r in rem_svc.list_due(db)]}


def _posponer_recordatorio(db: Session, a: dict) -> dict:
    r = _resolver_recordatorio(db, a["recordatorio"])
    cuando = datetime.fromisoformat(a["cuando"])
    rem_svc.snooze_reminder(db, r.id, cuando)
    return {"ok": True, "recordatorio": r.texto, "pospuesto_para": cuando.isoformat()}


def _marcar_recordatorio_resuelto(db: Session, a: dict) -> dict:
    r = _resolver_recordatorio(db, a["recordatorio"])
    rem_svc.resolve_reminder(db, r.id)
    return {"ok": True, "resuelto": r.texto}


def _eliminar_recordatorio(db: Session, a: dict) -> dict:
    r = _resolver_recordatorio(db, a["recordatorio"])
    return {
        "ok": True,
        "confirmar": {
            "tipo": "reminder",
            "id": str(r.id),
            "que": f"el recordatorio «{r.texto[:40]}»",
        },
    }


# --- Registro de tools ---


def _p(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


_STR = {"type": "string"}
_NUM = {"type": "number"}

TOOLS: list[Tool] = [
    # --- Hojas (notas) y cuadernos ---
    Tool(
        "crear_hoja",
        "Crea una hoja (nota) en el segundo cerebro. Título y cuaderno son opcionales.",
        _p({"contenido": _STR, "titulo": _STR, "cuaderno": _STR}, ["contenido"]),
        _crear_hoja,
    ),
    Tool(
        "anadir_a_hoja",
        "Añade texto al cuerpo de una hoja existente (identificada por su título). "
        "Si no existe una hoja con ese título, la crea con ese título.",
        _p({"hoja": _STR, "texto": _STR}, ["hoja", "texto"]),
        _anadir_a_hoja,
    ),
    Tool(
        "editar_hoja",
        "Edita el título y/o el cuerpo de una hoja existente (por su título actual).",
        _p(
            {"hoja": _STR, "nuevo_titulo": _STR, "nuevo_contenido": _STR},
            ["hoja"],
        ),
        _editar_hoja,
    ),
    Tool(
        "mover_hoja",
        "Mueve una hoja a un cuaderno.",
        _p({"hoja": _STR, "cuaderno": _STR}, ["hoja", "cuaderno"]),
        _mover_hoja,
    ),
    Tool(
        "eliminar_hoja",
        "Elimina una hoja (por su título). Pide confirmación antes de borrar.",
        _p({"hoja": _STR}, ["hoja"]),
        _eliminar_hoja,
    ),
    Tool(
        "buscar_hojas",
        "Busca hojas por significado (búsqueda semántica), no por palabra exacta.",
        _p({"texto": _STR, "limite": {"type": "integer"}}, ["texto"]),
        _buscar_hojas,
    ),
    Tool(
        "listar_hojas",
        "Lista las hojas de un cuaderno (o todas si no se indica cuaderno).",
        _p({"cuaderno": _STR}, []),
        _listar_hojas,
    ),
    Tool(
        "crear_cuaderno",
        "Crea un cuaderno para agrupar hojas.",
        _p({"nombre": _STR}, ["nombre"]),
        _crear_cuaderno,
    ),
    Tool(
        "listar_cuadernos",
        "Lista los cuadernos y cuántas hojas tiene cada uno.",
        _p({}, []),
        _listar_cuadernos,
    ),
    # --- Portafolios ---
    Tool(
        "crear_portafolio",
        "Crea un portafolio para agrupar proyectos.",
        _p({"nombre": _STR}, ["nombre"]),
        _crear_portafolio,
    ),
    Tool(
        "listar_portafolios",
        "Lista los portafolios y cuántos proyectos tiene cada uno.",
        _p({}, []),
        _listar_portafolios,
    ),
    Tool(
        "eliminar_portafolio",
        "Elimina un portafolio (los proyectos quedan sueltos). Pide confirmación.",
        _p({"portafolio": _STR}, ["portafolio"]),
        _eliminar_portafolio,
    ),
    # --- Proyectos ---
    Tool(
        "crear_proyecto",
        "Crea un proyecto que agrupa tareas y notas. Portafolio opcional (por nombre).",
        _p({"nombre": _STR, "descripcion": _STR, "portafolio": _STR}, ["nombre"]),
        _crear_proyecto,
    ),
    Tool(
        "listar_proyectos",
        "Lista los proyectos (o los de un portafolio si se indica).",
        _p({"portafolio": _STR}, []),
        _listar_proyectos,
    ),
    Tool(
        "ver_proyecto",
        "Muestra un proyecto con sus tareas y sus notas vinculadas (por su nombre).",
        _p({"proyecto": _STR}, ["proyecto"]),
        _ver_proyecto,
    ),
    Tool(
        "mover_proyecto",
        "Mueve un proyecto a un portafolio.",
        _p({"proyecto": _STR, "portafolio": _STR}, ["proyecto", "portafolio"]),
        _mover_proyecto,
    ),
    Tool(
        "archivar_proyecto",
        "Archiva un proyecto (pasa a estado terminado).",
        _p({"proyecto": _STR}, ["proyecto"]),
        _archivar_proyecto,
    ),
    Tool(
        "editar_proyecto",
        "Edita un proyecto (por su nombre): nuevo_nombre, descripción y/o estado "
        "(activo|pausado|terminado).",
        _p(
            {
                "proyecto": _STR,
                "nuevo_nombre": _STR,
                "descripcion": _STR,
                "estado": _STR,
            },
            ["proyecto"],
        ),
        _editar_proyecto,
    ),
    Tool(
        "crear_tarea",
        "Crea una tarea. Opcionalmente asociada a un proyecto y con fecha límite (YYYY-MM-DD).",
        _p(
            {"titulo": _STR, "proyecto": _STR, "fecha_limite": _STR},
            ["titulo"],
        ),
        _crear_tarea,
    ),
    Tool(
        "actualizar_avance_tarea",
        "Actualiza el porcentaje de avance de una tarea (referida por su título).",
        _p({"tarea": _STR, "avance_pct": {"type": "integer"}}, ["tarea", "avance_pct"]),
        _actualizar_avance_tarea,
    ),
    Tool(
        "completar_tarea",
        "Marca una tarea como terminada (referida por su título).",
        _p({"tarea": _STR}, ["tarea"]),
        _completar_tarea,
    ),
    Tool(
        "listar_tareas_pendientes",
        "Lista las tareas que no están terminadas.",
        _p({}, []),
        _listar_tareas_pendientes,
    ),
    Tool(
        "editar_tarea",
        "Edita una tarea (por su título): descripción, notas rápidas, estado "
        "(planeada|en_ejecucion|en_pausa|terminada) y fechas en YYYY-MM-DD "
        "(fecha_limite = fin planeado; también fecha_inicio_plan, fecha_inicio_real, "
        "fecha_fin_real).",
        _p(
            {
                "tarea": _STR,
                "descripcion": _STR,
                "notas": _STR,
                "estado": _STR,
                "fecha_limite": _STR,
                "fecha_inicio_plan": _STR,
                "fecha_inicio_real": _STR,
                "fecha_fin_real": _STR,
            },
            ["tarea"],
        ),
        _editar_tarea,
    ),
    Tool(
        "eliminar_tarea",
        "Elimina una tarea (por su título). Pide confirmación antes de borrar.",
        _p({"tarea": _STR}, ["tarea"]),
        _eliminar_tarea,
    ),
    Tool(
        "listar_tareas",
        "Lista las tareas de un proyecto (o todas si no se indica proyecto).",
        _p({"proyecto": _STR}, []),
        _listar_tareas,
    ),
    Tool(
        "tareas_de_hoy",
        "Lista las tareas que vencen hoy o están vencidas y sin terminar.",
        _p({}, []),
        _tareas_de_hoy,
    ),
    Tool(
        "agregar_item_checklist",
        "Añade un ítem (paso) al checklist de una tarea (por su título).",
        _p({"tarea": _STR, "texto": _STR}, ["tarea", "texto"]),
        _agregar_item_checklist,
    ),
    Tool(
        "marcar_item_checklist",
        "Marca (hecho=true) o desmarca (hecho=false) un ítem del checklist de una "
        "tarea. El ítem se identifica por su texto. Al 100% la tarea se termina sola.",
        _p(
            {"tarea": _STR, "item": _STR, "hecho": {"type": "boolean"}},
            ["tarea", "item"],
        ),
        _marcar_item_checklist,
    ),
    Tool(
        "quitar_item_checklist",
        "Quita un ítem del checklist de una tarea (identificado por su texto).",
        _p({"tarea": _STR, "item": _STR}, ["tarea", "item"]),
        _quitar_item_checklist,
    ),
    Tool(
        "agregar_nota_a_tarea",
        "Crea una hoja (nota) y la vincula a una tarea. Para dejar apuntes ricos y "
        "buscables asociados a la tarea. Título opcional.",
        _p({"tarea": _STR, "contenido": _STR, "titulo": _STR}, ["tarea", "contenido"]),
        _agregar_nota_a_tarea,
    ),
    Tool(
        "registrar_gasto",
        "Registra un gasto. La categoría debe ser una de las disponibles; la cuenta, una existente.",
        _p(
            {"monto": _NUM, "categoria": _STR, "cuenta": _STR, "nota": _STR},
            ["monto", "categoria", "cuenta"],
        ),
        _registrar_gasto,
    ),
    Tool(
        "registrar_ingreso",
        "Registra un ingreso en una cuenta con una categoría.",
        _p(
            {"monto": _NUM, "categoria": _STR, "cuenta": _STR, "nota": _STR},
            ["monto", "categoria", "cuenta"],
        ),
        _registrar_ingreso,
    ),
    Tool(
        "transferir",
        "Transfiere dinero entre dos cuentas propias (mueve el saldo).",
        _p(
            {"monto": _NUM, "cuenta_origen": _STR, "cuenta_destino": _STR},
            ["monto", "cuenta_origen", "cuenta_destino"],
        ),
        _transferir,
    ),
    Tool(
        "consultar_saldo",
        "Consulta el saldo de una cuenta.",
        _p({"cuenta": _STR}, ["cuenta"]),
        _consultar_saldo,
    ),
    Tool(
        "gastos_del_mes",
        "Resumen de los gastos del mes actual, con desglose por categoría.",
        _p({}, []),
        _gastos_del_mes,
    ),
    Tool(
        "crear_cuenta",
        "Crea una cuenta. tipo sugerido: efectivo|banco|ahorros. saldo_inicial opcional.",
        _p({"nombre": _STR, "tipo": _STR, "saldo_inicial": _NUM}, ["nombre"]),
        _crear_cuenta,
    ),
    Tool(
        "listar_cuentas",
        "Lista las cuentas con su saldo y el total.",
        _p({}, []),
        _listar_cuentas,
    ),
    Tool(
        "crear_categoria",
        "Crea una categoría de finanzas.",
        _p({"nombre": _STR}, ["nombre"]),
        _crear_categoria,
    ),
    Tool(
        "listar_movimientos",
        "Lista los movimientos recientes (de una cuenta si se indica).",
        _p({"cuenta": _STR}, []),
        _listar_movimientos,
    ),
    Tool(
        "eliminar_ultimo_movimiento",
        "Elimina el último movimiento registrado (revierte el saldo). Pide "
        "confirmación antes de borrar.",
        _p({}, []),
        _eliminar_ultimo_movimiento,
    ),
    Tool(
        "definir_presupuesto",
        "Define un presupuesto mensual. Con categoría es por categoría; sin "
        "categoría es el presupuesto global del mes.",
        _p({"tope": _NUM, "categoria": _STR}, ["tope"]),
        _definir_presupuesto,
    ),
    Tool(
        "avance_presupuesto",
        "Consulta el avance de un presupuesto (gastado vs tope este mes). Sin "
        "categoría consulta el global.",
        _p({"categoria": _STR}, []),
        _avance_presupuesto,
    ),
    Tool(
        "listar_presupuestos",
        "Lista los presupuestos con su avance del mes.",
        _p({}, []),
        _listar_presupuestos,
    ),
    Tool(
        "crear_recordatorio",
        "Crea un recordatorio. `disparar_en` en ISO 8601 (usa la fecha/hora actual del contexto).",
        _p({"texto": _STR, "disparar_en": _STR}, ["texto"]),
        _crear_recordatorio,
    ),
    Tool(
        "crear_responsabilidad",
        "Crea un compromiso recurrente. recurrencia: diaria|semanal|mensual|trimestral|anual|cada_N_dias. proximo_venc en YYYY-MM-DD.",
        _p(
            {"nombre": _STR, "recurrencia": _STR, "proximo_venc": _STR, "monto": _NUM},
            ["nombre", "recurrencia", "proximo_venc"],
        ),
        _crear_responsabilidad,
    ),
    Tool(
        "listar_responsabilidades",
        "Lista las responsabilidades por próximo vencimiento.",
        _p({}, []),
        _listar_responsabilidades,
    ),
    Tool(
        "cumplir_responsabilidad",
        "Marca una responsabilidad como cumplida (por su nombre); recalcula el "
        "próximo vencimiento según su recurrencia.",
        _p({"responsabilidad": _STR}, ["responsabilidad"]),
        _cumplir_responsabilidad,
    ),
    Tool(
        "editar_responsabilidad",
        "Edita una responsabilidad (por su nombre): nuevo_nombre, recurrencia, "
        "proximo_venc (YYYY-MM-DD) y/o monto.",
        _p(
            {
                "responsabilidad": _STR,
                "nuevo_nombre": _STR,
                "recurrencia": _STR,
                "proximo_venc": _STR,
                "monto": _NUM,
            },
            ["responsabilidad"],
        ),
        _editar_responsabilidad,
    ),
    Tool(
        "eliminar_responsabilidad",
        "Elimina una responsabilidad (por su nombre). Pide confirmación.",
        _p({"responsabilidad": _STR}, ["responsabilidad"]),
        _eliminar_responsabilidad,
    ),
    # --- Recordatorios ---
    Tool(
        "listar_recordatorios",
        "Lista los recordatorios pendientes (sin resolver).",
        _p({}, []),
        _listar_recordatorios,
    ),
    Tool(
        "recordatorios_vencidos",
        "Lista los recordatorios cuyo momento ya llegó y siguen sin resolver.",
        _p({}, []),
        _recordatorios_vencidos,
    ),
    Tool(
        "posponer_recordatorio",
        "Pospone un recordatorio (por su texto) a `cuando` en ISO 8601 (usa la "
        "fecha/hora actual del contexto).",
        _p({"recordatorio": _STR, "cuando": _STR}, ["recordatorio", "cuando"]),
        _posponer_recordatorio,
    ),
    Tool(
        "resolver_recordatorio",
        "Marca un recordatorio como resuelto (por su texto).",
        _p({"recordatorio": _STR}, ["recordatorio"]),
        _marcar_recordatorio_resuelto,
    ),
    Tool(
        "eliminar_recordatorio",
        "Elimina un recordatorio (por su texto). Pide confirmación.",
        _p({"recordatorio": _STR}, ["recordatorio"]),
        _eliminar_recordatorio,
    ),
]

_POR_NOMBRE = {t.name: t for t in TOOLS}


def openai_tools() -> list[dict]:
    """Las tools en el formato que espera la API OpenAI-compatible."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in TOOLS
    ]


def dispatch(db: Session, name: str, arguments: dict) -> dict:
    """Ejecuta una tool. Los errores de negocio se devuelven como resultado
    (no excepciones) para que el modelo pueda explicarlos al usuario."""
    tool = _POR_NOMBRE.get(name)
    if tool is None:
        return {"ok": False, "error": f"Herramienta desconocida: {name}"}
    try:
        return tool.handler(db, arguments)
    except (ValueError, KeyError) as exc:
        return {"ok": False, "error": str(exc)}
