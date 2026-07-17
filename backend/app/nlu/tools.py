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

from app.models.finances import Account, Category
from app.models.projects import Project
from app.models.tasks import Task
from app.schemas.finances import AccountCreate, TransactionCreate, TransactionTipo
from app.schemas.notes import NoteCreate
from app.schemas.projects import ProjectCreate
from app.schemas.reminders import ReminderCreate
from app.schemas.responsibilities import ResponsibilityCreate
from app.schemas.tasks import TaskCreate
from app.services import finances as fin
from app.services import notes as notes_svc
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


def _money(v: Any) -> str:
    return f"{float(v):.2f}"


# --- Handlers ---


def _crear_nota(db: Session, a: dict) -> dict:
    nota = notes_svc.create_note(db, NoteCreate(contenido=a["contenido"]))
    return {"ok": True, "nota_id": str(nota.id), "contenido": nota.contenido}


def _buscar_notas(db: Session, a: dict) -> dict:
    res = notes_svc.search_notes(db, a["texto"], int(a.get("limite", 5)))
    return {
        "ok": True,
        "resultados": [
            {"contenido": n.contenido, "similitud": round(s, 3)} for n, s in res
        ],
    }


def _crear_proyecto(db: Session, a: dict) -> dict:
    p = proj_svc.create_project(
        db, ProjectCreate(nombre=a["nombre"], descripcion=a.get("descripcion"))
    )
    return {"ok": True, "proyecto_id": str(p.id), "nombre": p.nombre}


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
    tareas = task_svc.list_pendientes(db)
    return {
        "ok": True,
        "tareas": [
            {"titulo": t.titulo, "estado": t.estado, "avance_pct": t.avance_pct}
            for t in tareas
        ],
    }


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


# --- Registro de tools ---


def _p(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


_STR = {"type": "string"}
_NUM = {"type": "number"}

TOOLS: list[Tool] = [
    Tool(
        "crear_nota",
        "Guarda una nota de texto libre en el segundo cerebro.",
        _p({"contenido": _STR}, ["contenido"]),
        _crear_nota,
    ),
    Tool(
        "buscar_notas",
        "Busca notas por significado (búsqueda semántica), no por palabra exacta.",
        _p({"texto": _STR, "limite": {"type": "integer"}}, ["texto"]),
        _buscar_notas,
    ),
    Tool(
        "crear_proyecto",
        "Crea un proyecto que agrupa tareas y notas.",
        _p({"nombre": _STR, "descripcion": _STR}, ["nombre"]),
        _crear_proyecto,
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
