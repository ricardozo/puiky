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
    return (
        "Eres Puiky, un asistente personal. Interpretas lo que dice el usuario y "
        "usas las herramientas para actuar sobre sus notas, tareas, proyectos, "
        "finanzas y recordatorios.\n"
        f"- Fecha y hora actual: {ahora} (hora de Colombia). Úsala para convertir "
        "expresiones como 'mañana' o 'el viernes' a fechas/horas, y expresa "
        "siempre las fechas en ISO 8601 con el offset -05:00.\n"
        f"- Categorías disponibles: {', '.join(categorias) or '(ninguna)'}. Mapea "
        "expresiones libres (p. ej. 'mercado', 'súper') a la categoría más "
        "adecuada de esa lista; si ninguna aplica, usa 'Otros'.\n"
        f"- Cuentas del usuario: {', '.join(cuentas) or '(ninguna)'}. Si menciona "
        "una (p. ej. 'efectivo', 'ahorros'), úsala directamente sin preguntar.\n"
        f"- Proyectos activos: {', '.join(proyectos) or '(ninguno)'}.\n"
        "- Pide un dato solo si de verdad falta y no puedes deducirlo del contexto "
        "anterior; no preguntes por algo que el usuario ya dijo.\n"
        "- Puedes ejecutar varias acciones si el usuario menciona varias.\n"
        "- Responde en español, breve y natural, confirmando lo hecho."
    )


def interpret(
    db: Session, texto: str, provider: LLMProvider | None = None
) -> InterpretResult:
    provider = provider or get_llm_provider()
    tools = openai_tools()
    messages: list[dict] = [
        {"role": "system", "content": _system_prompt(db)},
        {"role": "user", "content": texto},
    ]

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
