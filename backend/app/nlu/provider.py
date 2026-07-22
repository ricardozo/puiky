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


# Bloques de razonamiento de Qwen3 en el contenido (se descartan siempre).
_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


class RealLLMProvider:
    """Habla con Ollama por su API NATIVA (/api/chat).

    Se usa la nativa (y no la OpenAI-compatible) por dos razones críticas:
    - `options.num_ctx` por petición: el default de Ollama (4096) TRUNCABA
      nuestro prompt (~7k tokens con 67 tools) y el modelo perdía reglas y
      herramientas — fuente de gran parte de la inestabilidad observada.
    - `think: false`: apaga de verdad el razonamiento largo de Qwen3 (el switch
      suave /no_think por prompt no es confiable).
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,  # no se usa en la API nativa; se conserva por firma
        no_think: bool = True,
        num_ctx: int = 12288,
    ) -> None:
        import httpx  # import perezoso

        # llm_base_url viene como http://host:11434/v1 → raíz nativa sin /v1
        self._root = base_url.rstrip("/").removesuffix("/v1")
        self._http = httpx.Client(timeout=300.0)
        self._model = model
        self._no_think = no_think
        self._num_ctx = num_ctx

    def chat(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": self._num_ctx},
        }
        if self._no_think:
            payload["think"] = False
        if tools:
            payload["tools"] = tools
        r = self._http.post(f"{self._root}/api/chat", json=payload)
        r.raise_for_status()
        msg = r.json().get("message") or {}
        calls: list[ToolCall] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            args = fn.get("arguments") or {}
            if isinstance(args, str):  # por si llegara serializado
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            calls.append(ToolCall(name=fn.get("name", ""), arguments=args))
        content = msg.get("content") or None
        if content:
            content = _THINK_RE.sub("", content).strip()
        return LLMResponse(content=content, tool_calls=calls)


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
            return ToolCall("buscar_hojas", {"texto": q})

        if any(k in t for k in ["añade a la hoja", "agrega a la hoja", "en la hoja"]):
            hoja = _despues_de(texto, ["hoja"]) or ""
            hoja = hoja.split(":")[0].split(" añade")[0].split(" agrega")[0].strip()
            texto_add = texto.split(":", 1)[1].strip() if ":" in texto else texto
            return ToolCall("anadir_a_hoja", {"hoja": hoja, "texto": texto_add})

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

        if any(k in t for k in ["nota", "anota", "apunta", "hoja"]):
            return ToolCall("crear_hoja", {"contenido": texto})

        return None


@lru_cache
def get_llm_provider() -> LLMProvider:
    s = get_settings()
    if s.llm_backend == "real":
        return RealLLMProvider(
            s.llm_base_url,
            s.llm_model,
            s.llm_api_key,
            no_think=s.llm_no_think,
            num_ctx=s.llm_num_ctx,
        )
    return FakeLLMProvider()
