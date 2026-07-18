"""Orquestador de la interpretación: texto del usuario → tool calls → acciones.

Un solo turno con una ronda de herramientas: se pide al modelo qué hacer, se
ejecutan las tools (posiblemente varias, multi-intención) y se le devuelven los
resultados para que redacte una confirmación natural.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finances import Account, Category
from app.models.notebooks import Notebook
from app.models.portfolios import Portfolio
from app.models.projects import Project
from app.nlu.provider import LLMProvider, get_llm_provider
from app.nlu.tools import dispatch, openai_tools
from app.timeutils import now_local


@dataclass
class Accion:
    tool: str
    argumentos: dict[str, Any]
    resultado: dict[str, Any]


@dataclass
class InterpretResult:
    respuesta: str
    acciones: list[Accion] = field(default_factory=list)


def _system_prompt(db: Session) -> str:
    ahora = now_local().isoformat(timespec="minutes")
    categorias = [
        c.nombre
        for c in db.execute(
            select(Category).where(Category.activa.is_(True)).order_by(Category.nombre)
        ).scalars()
    ]
    cuentas = [
        a.nombre
        for a in db.execute(select(Account).order_by(Account.nombre)).scalars()
    ]
    proyectos = [
        p.nombre
        for p in db.execute(
            select(Project).where(Project.estado != "terminado").order_by(Project.nombre)
        ).scalars()
    ]
    cuadernos = [
        nb.nombre
        for nb in db.execute(select(Notebook).order_by(Notebook.nombre)).scalars()
    ]
    portafolios = [
        pf.nombre
        for pf in db.execute(select(Portfolio).order_by(Portfolio.nombre)).scalars()
    ]
    return (
        "Eres Puiky, un asistente personal (un 'segundo cerebro'). Interpretas lo "
        "que dice el usuario y usas las herramientas para actuar.\n"
        "Conceptos: una HOJA es una nota con título (opcional) y un cuerpo que "
        "puede crecer; vive en un CUADERNO (que agrupa hojas). Para agregar algo a "
        "una hoja que ya existe usa 'anadir_a_hoja' (identifícala por su título); "
        "para una idea nueva usa 'crear_hoja'.\n"
        f"- Fecha y hora actual: {ahora} (hora de Colombia). Convierte 'mañana', "
        "'el viernes', etc. a fechas/horas ISO 8601 con offset -05:00.\n"
        f"- Cuadernos: {', '.join(cuadernos) or '(ninguno)'}.\n"
        f"- Categorías: {', '.join(categorias) or '(ninguna)'}. Mapea expresiones "
        "libres ('mercado', 'súper') a la más adecuada; si ninguna aplica, 'Otros'.\n"
        f"- Cuentas: {', '.join(cuentas) or '(ninguna)'}. Úsalas sin preguntar.\n"
        f"- Portafolios: {', '.join(portafolios) or '(ninguno)'} (agrupan proyectos).\n"
        f"- Proyectos activos: {', '.join(proyectos) or '(ninguno)'}.\n"
        "- Pide un dato solo si de verdad falta; no preguntes por algo ya dicho.\n"
        "- Puedes ejecutar varias acciones si el usuario menciona varias.\n"
        "- Responde en español, breve y natural, confirmando lo hecho."
    )


def interpret(
    db: Session,
    texto: str,
    provider: LLMProvider | None = None,
    historial: list | None = None,
) -> InterpretResult:
    provider = provider or get_llm_provider()
    tools = openai_tools()
    messages: list[dict] = [{"role": "system", "content": _system_prompt(db)}]
    # Memoria de conversación: turnos previos (para aclaraciones y contexto).
    for m in historial or []:
        rol = getattr(m, "rol", None) or m.get("rol")
        contenido = getattr(m, "texto", None) or m.get("texto")
        if rol in ("user", "assistant") and contenido:
            messages.append({"role": rol, "content": contenido})
    messages.append({"role": "user", "content": texto})

    resp = provider.chat(messages, tools)
    if not resp.tool_calls:
        return InterpretResult(respuesta=resp.content or "")

    # Registra la decisión del modelo (necesario para adjuntar los resultados).
    messages.append(
        {
            "role": "assistant",
            "content": resp.content or "",
            "tool_calls": [
                {
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for i, tc in enumerate(resp.tool_calls)
            ],
        }
    )

    acciones: list[Accion] = []
    for i, tc in enumerate(resp.tool_calls):
        resultado = dispatch(db, tc.name, tc.arguments)
        acciones.append(Accion(tool=tc.name, argumentos=tc.arguments, resultado=resultado))
        messages.append(
            {
                "role": "tool",
                "tool_call_id": f"call_{i}",
                "content": json.dumps(resultado, ensure_ascii=False),
            }
        )

    # Segunda llamada SIN tools: solo queremos la confirmación en texto.
    final = provider.chat(messages, [])
    return InterpretResult(respuesta=final.content or "", acciones=acciones)
