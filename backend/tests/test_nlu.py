"""Tests de la capa NLU que no requieren BD ni modelo: el intérprete fake y
el formato de las tools. La interpretación real (Qwen) se prueba a mano."""

from app.nlu.provider import FakeLLMProvider
from app.nlu.tools import openai_tools


def _tool_de(texto: str) -> str | None:
    resp = FakeLLMProvider().chat(
        [{"role": "user", "content": texto}], openai_tools()
    )
    return resp.tool_calls[0].name if resp.tool_calls else None


def test_tools_formato_openai() -> None:
    tools = openai_tools()
    assert tools, "debe haber tools registradas"
    for t in tools:
        assert t["type"] == "function"
        f = t["function"]
        assert f["name"] and f["description"]
        assert f["parameters"]["type"] == "object"


def test_fake_reconoce_intenciones() -> None:
    assert _tool_de("anota que debo llamar al banco") == "crear_hoja"
    assert _tool_de("busca sobre facturación") == "buscar_hojas"
    assert _tool_de("gasté 12000 en comida con efectivo") == "registrar_gasto"
    assert _tool_de("cuánto tengo en ahorros") == "consultar_saldo"
    assert _tool_de("recuérdame llamar a Juan el viernes") == "crear_recordatorio"


def test_fake_extrae_monto() -> None:
    resp = FakeLLMProvider().chat(
        [{"role": "user", "content": "gasté 12.500 en comida con efectivo"}],
        openai_tools(),
    )
    assert resp.tool_calls[0].arguments["monto"] == 12500


def test_fake_fase_confirmacion() -> None:
    # Con un mensaje role=tool presente, resume en vez de volver a llamar tools.
    resp = FakeLLMProvider().chat(
        [
            {"role": "user", "content": "x"},
            {"role": "tool", "content": '{"ok": true}'},
        ],
        openai_tools(),
    )
    assert resp.tool_calls == []
    assert resp.content
