"""Orquestador de la interpretación: texto del usuario → tool calls → acciones.

Un solo turno con una ronda de herramientas: se pide al modelo qué hacer, se
ejecutan las tools (posiblemente varias, multi-intención) y se le devuelven los
resultados para que redacte una confirmación natural.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.finances import Account, Category
from app.models.market import MarketProduct
from app.models.notebooks import Notebook
from app.models.portfolios import Portfolio
from app.models.projects import Project
from app.models.responsibilities import Responsibility
from app.nlu.provider import LLMProvider, ToolCall, get_llm_provider
from app.nlu.tools import dispatch, openai_tools
from app.timeutils import now_local

# Objeto JSON con posible anidación de un nivel (para {"name":..,"arguments":{..}})
_OBJ = re.compile(r"\{(?:[^{}]|\{[^{}]*\})*\}")

_RECUERDAME = re.compile(r"\brecu[eé]rdame\b", re.IGNORECASE)

# «130mil» pegado → «130 mil» (el modelo lo lee mucho mejor separado).
_PEGADO = re.compile(r"(\d)(mil\b|mill[oó]n(?:es)?\b)", re.IGNORECASE)
# Números dichos «en miles» y mención de millones, para validar magnitudes.
_N_MIL = re.compile(r"\b(\d+)\s*mil\b", re.IGNORECASE)
_MILLON = re.compile(r"mill[oó]n", re.IGNORECASE)
_TOOLS_MONTO = {"registrar_gasto", "registrar_ingreso", "transferir", "pagar_responsabilidad"}


def _corregir_magnitud(texto: str, tc: ToolCall) -> None:
    """Si el usuario dijo «N mil» (sin mencionar millones) y el modelo puso
    N × 1.000.000, corrige a N × 1.000. Muta los argumentos del tool call."""
    if tc.name not in _TOOLS_MONTO or _MILLON.search(texto):
        return
    try:
        monto = float(tc.arguments.get("monto") or 0)
    except (TypeError, ValueError):
        return
    for n in _N_MIL.findall(texto):
        if monto == float(n) * 1_000_000:
            tc.arguments["monto"] = int(n) * 1000
            return


def _corregir_tool_calls(texto: str, calls: list[ToolCall]) -> list[ToolCall]:
    """Correcciones deterministas de fallos conocidos del modelo.

    «Recuérdame…» debe ser un recordatorio, pero Qwen a veces lo convierte en
    responsabilidad (con fechas alucinadas). Aquí se reencauza sin depender del
    prompt. No se pasa la fecha del modelo: el handler usa 'ahora' por defecto."""
    out: list[ToolCall] = []
    for tc in calls:
        if tc.name == "crear_responsabilidad" and _RECUERDAME.search(texto):
            args: dict = {"texto": tc.arguments.get("nombre") or texto}
            if tc.arguments.get("recurrencia"):
                args["recurrencia"] = tc.arguments["recurrencia"]
            out.append(ToolCall(name="crear_recordatorio", arguments=args))
        else:
            _corregir_magnitud(texto, tc)
            out.append(tc)
    return out


def _tool_calls_desde_texto(content: str | None) -> list[ToolCall]:
    """Rescata tool calls que el modelo emitió como TEXTO en vez de usar el canal
    nativo. Qwen (vía Ollama) a veces «narra» el {"name":..,"arguments":..} en el
    contenido; sin esto la acción nunca se ejecutaría."""
    if not content:
        return []
    validos = {t["function"]["name"] for t in openai_tools()}
    calls: list[ToolCall] = []
    for m in _OBJ.finditer(content):
        frag = m.group(0)
        if '"name"' not in frag or '"arguments"' not in frag:
            continue
        try:
            obj = json.loads(frag)
        except json.JSONDecodeError:
            continue
        nombre, args = obj.get("name"), obj.get("arguments")
        if nombre in validos and isinstance(args, dict):
            calls.append(ToolCall(name=nombre, arguments=args))
    return calls


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
    productos = [
        p.nombre
        for p in db.execute(
            select(MarketProduct)
            .where(MarketProduct.activo.is_(True))
            .order_by(MarketProduct.nombre)
        ).scalars()
    ]
    responsabilidades = [
        r.nombre
        for r in db.execute(
            select(Responsibility).order_by(Responsibility.nombre)
        ).scalars()
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
        "- Al listar tareas, si una trae el campo 'recurrente', indícalo con 🔁 y "
        "su periodicidad (p. ej. «Cuenta de cobro COLEF 🔁 recurrente (mensual)»).\n"
        f"- Cuadernos: {', '.join(cuadernos) or '(ninguno)'}.\n"
        f"- Categorías: {', '.join(categorias) or '(ninguna)'}. Mapea expresiones "
        "libres ('mercado', 'súper') a la más adecuada; si ninguna aplica, 'Otros'.\n"
        f"- Cuentas: {', '.join(cuentas) or '(ninguna)'}. Úsalas sin preguntar.\n"
        "- REGLA DE DINERO: si el usuario dice que gastó, pagó o compró y menciona "
        "un monto (p. ej. «gasté 15 mil en agua y leche», «pagué 19 mil el "
        "desayuno») es SIEMPRE registrar_gasto, con ese monto, la cuenta indicada "
        "y una categoría de la lista (mapea 'agua y leche', 'desayuno', 'súper' → "
        "Mercado o Comida). NUNCA uses registrar_compra_mercado para esto. "
        "registrar_compra_mercado NO mueve dinero y solo aplica si <algo> coincide "
        "con un nombre de 'Productos de mercado' de abajo; si no está en esa "
        "lista, es un gasto. Ante la duda, registrar_gasto.\n"
        "- REGLA DE MONTOS (¡crítico, no infles!): 'mil'/'k'/'lucas' = ×1.000; "
        "'millón'/'millones'/'M' = ×1.000.000. Ejemplos exactos: «130 mil»→130000, "
        "«130mil»→130000, «cincuenta mil»→50000, «20 lucas»→20000, «2 millones»→"
        "2000000, «1,5 millones»→1500000. «130 mil» son ciento treinta mil, NUNCA "
        "ciento treinta millones. Si no dicen 'millón', el monto no llega a millones.\n"
        f"- Portafolios: {', '.join(portafolios) or '(ninguno)'} (agrupan proyectos).\n"
        f"- Proyectos activos: {', '.join(proyectos) or '(ninguno)'}.\n"
        f"- Productos de mercado: {', '.join(productos) or '(ninguno)'}. Para "
        "«¿qué me toca comprar?» usa que_toca_comprar.\n"
        f"- Pagos recurrentes (responsabilidades): "
        f"{', '.join(responsabilidades) or '(ninguno)'}. Si el usuario dice que "
        "pagó uno de estos (p. ej. «pagué la administración», «ya pagué el "
        "arriendo») usa pagar_responsabilidad (crea el gasto con la cuenta y "
        "monto guardados y avanza la fecha), NO registrar_gasto.\n"
        "- «Recuérdame <algo>» es SIEMPRE crear_recordatorio (con recurrencia "
        "si dice «cada mes/semana/día/año»; disparar_en cercano: hoy o mañana "
        "si no dan fecha), NUNCA crear_responsabilidad. Una responsabilidad "
        "solo se crea si piden explícitamente una responsabilidad o un pago "
        "recurrente con monto.\n"
        "- Modo compra (ir al súper): «voy a comprar / arma la lista» → "
        "iniciar_compra (y agregar_sugeridos_compra para sumar lo que toca). "
        "«agrega X a la lista» → agregar_a_lista. «compré X [a tanto]» → "
        "marcar_comprado. «¿qué me falta?» → que_me_falta. «terminé / cierra la "
        "compra [con tal cuenta]» → cerrar_compra. «cancela / me arrepentí» → "
        "cancelar_compra.\n"
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
    # «130mil» → «130 mil»: separado, el modelo interpreta bien la magnitud.
    texto = _PEGADO.sub(r"\1 \2", texto)
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
    # Usa las tool calls nativas; si no hay, rescata las que el modelo pudo haber
    # emitido como texto (Qwen a veces lo hace y la acción se perdería).
    tool_calls = resp.tool_calls or _tool_calls_desde_texto(resp.content)
    if not tool_calls:
        return InterpretResult(respuesta=resp.content or "")
    tool_calls = _corregir_tool_calls(texto, tool_calls)

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
                for i, tc in enumerate(tool_calls)
            ],
        }
    )

    acciones: list[Accion] = []
    for i, tc in enumerate(tool_calls):
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
    respuesta = final.content or ""
    # Blindaje: si el modelo vuelve a «narrar» un JSON de tool call en vez de
    # confirmar, no se lo mostramos al usuario; armamos una confirmación simple.
    if not respuesta.strip() or _tool_calls_desde_texto(respuesta):
        respuesta = _confirmacion_fallback(acciones)
    return InterpretResult(respuesta=respuesta, acciones=acciones)


def _confirmacion_fallback(acciones: list[Accion]) -> str:
    """Confirmación armada a mano cuando el modelo no redacta bien la 2ª pasada."""
    ok = [a for a in acciones if a.resultado.get("ok", True)]
    err = [a for a in acciones if not a.resultado.get("ok", True)]
    partes: list[str] = []
    if ok:
        partes.append("Listo, lo registré." if len(ok) == 1 else f"Listo, registré {len(ok)} cosas.")
    for a in err:
        partes.append(f"No pude con «{a.tool}»: {a.resultado.get('error', 'error')}")
    return " ".join(partes) or "Listo."
