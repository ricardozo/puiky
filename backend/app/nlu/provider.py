"""Proveedor de LLM con tool calling. Interfaz + backend real y fake.

- RealLLMProvider: cliente OpenAI-compatible (Ollama sirviendo Qwen). El mismo
  código sirve para enrutar a un modelo de API más capaz cambiando base_url.
- FakeLLMProvider: intérprete determinista por reglas (regex/palabras clave).
  NO es NLU de verdad; existe para desarrollar y testear el circuito completo
  (tools + services) sin depender de un modelo.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

from app.config import get_settings


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(Protocol):
    def chat(
        self, messages: list[dict], tools: list[dict]
    ) -> LLMResponse: ...


class RealLLMProvider:
    """Habla con un endpoint OpenAI-compatible (Ollama/Qwen)."""

    def __init__(self, base_url: str, model: str, api_key: str) -> None:
        from openai import OpenAI  # import perezoso

        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools or None,
            temperature=0,
        )
        msg = resp.choices[0].message
        calls: list[ToolCall] = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(name=tc.function.name, arguments=args))
        return LLMResponse(content=msg.content, tool_calls=calls)


# --- Backend fake: intérprete determinista ---

_NUM = r"(\d[\d.\s]*)"


def _num(texto: str) -> float | None:
    m = re.search(_NUM, texto)
    if not m:
        return None
    return float(m.group(1).replace(".", "").replace(" ", ""))


def _despues_de(texto: str, marcadores: list[str]) -> str | None:
    for mk in marcadores:
        m = re.search(rf"{mk}\s+(.+)", texto, re.IGNORECASE)
        if m:
            return m.group(1).strip(" .")
    return None


class FakeLLMProvider:
    """Reglas mínimas para las intenciones más comunes. Determinista."""

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        # Fase de confirmación: si ya hay resultados de tools, resumirlos.
        if any(m.get("role") == "tool" for m in messages):
            hechos = [m.get("content", "") for m in messages if m.get("role") == "tool"]
            return LLMResponse(content="Listo. " + " ".join(hechos))

        texto = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                texto = m.get("content", "")
                break
        t = texto.lower()

        call = self._interpretar(texto, t)
        if call is None:
            return LLMResponse(
                content="(fake) No reconocí una acción en ese texto."
            )
        return LLMResponse(tool_calls=[call])

    def _interpretar(self, texto: str, t: str) -> ToolCall | None:
        if any(k in t for k in ["busca", "buscar", "qué pensé", "que pense"]):
            q = _despues_de(texto, ["sobre", "acerca de", "busca", "buscar"]) or texto
            return ToolCall("buscar_notas", {"texto": q})

        if any(k in t for k in ["recuérdame", "recuerdame", "recordarme"]):
            return ToolCall("crear_recordatorio", {"texto": texto})

        if any(k in t for k in ["gasté", "gaste", "gasto", "pagué", "pague", "compré", "compre"]):
            args: dict[str, Any] = {"monto": _num(t)}
            cat = _despues_de(t, ["en", "de"])
            cuenta = _despues_de(t, ["con la", "desde la", "de la cuenta", "con"])
            if cat:
                args["categoria"] = cat.split(" con ")[0].strip()
            if cuenta:
                args["cuenta"] = cuenta
            return ToolCall("registrar_gasto", args)

        if any(k in t for k in ["ingreso", "me pagaron", "recibí", "recibi"]):
            return ToolCall(
                "registrar_ingreso",
                {"monto": _num(t), "cuenta": _despues_de(t, ["en la", "a la", "en"])},
            )

        if "saldo" in t or "cuánto tengo" in t or "cuanto tengo" in t:
            return ToolCall(
                "consultar_saldo", {"cuenta": _despues_de(t, ["de la", "en", "de"]) or ""}
            )

        if "tarea" in t:
            titulo = _despues_de(texto, ["tarea", "que"]) or texto
            return ToolCall("crear_tarea", {"titulo": titulo})

        if "proyecto" in t:
            return ToolCall(
                "crear_proyecto",
                {"nombre": _despues_de(texto, ["proyecto"]) or texto},
            )

        if any(k in t for k in ["nota", "anota", "apunta"]):
            return ToolCall("crear_nota", {"contenido": texto})

        return None


@lru_cache
def get_llm_provider() -> LLMProvider:
    s = get_settings()
    if s.llm_backend == "real":
        return RealLLMProvider(s.llm_base_url, s.llm_model, s.llm_api_key)
    return FakeLLMProvider()
