"""Transcripción de audio a texto (Whisper). Interfaz + real y fake.

- RealTranscriber: faster-whisper local (descarga el modelo la primera vez y lo
  cachea). Corre en CPU; no depende de torch/CUDA.
- FakeTranscriber: devuelve un texto fijo para probar el flujo audio→NLU sin
  procesar audio real.
"""

from __future__ import annotations

import io
from functools import lru_cache
from typing import Protocol

from app.config import get_settings

# Frase fija del backend fake: permite demostrar el circuito audio → interpret.
_FAKE_TEXTO = "crea una nota que diga que probé la transcripción de audio"


class Transcriber(Protocol):
    def transcribe(self, audio: bytes) -> str: ...


# Sesga la decodificación hacia el vocabulario real del asistente (platas
# colombianas, cuentas, mercado); mejora mucho los "30 mil" y nombres propios.
_PROMPT_DOMINIO = (
    "Nota de voz en español de Colombia para un asistente personal de gastos, "
    "mercado, tareas y recordatorios. Ejemplos: gasté 35 mil en almuerzo con "
    "Bancolombia; transfiere 200 mil a ahorro; recuérdame pagar el arriendo el "
    "viernes; agua en botella 2 por 5 mil cada una."
)


class RealTranscriber:
    def __init__(self, model_size: str) -> None:
        from faster_whisper import WhisperModel  # import perezoso

        # int8 en CPU: rápido y ligero, suficiente para notas de voz.
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio: bytes) -> str:
        segments, _ = self._model.transcribe(
            io.BytesIO(audio),
            language="es",
            initial_prompt=_PROMPT_DOMINIO,
            # Recorta silencios/ruido antes de decodificar.
            vad_filter=True,
            # Cada nota de voz es corta e independiente: sin arrastre entre
            # segmentos, que en audios cortos produce alucinaciones repetidas.
            condition_on_previous_text=False,
        )
        return "".join(seg.text for seg in segments).strip()


class FakeTranscriber:
    def transcribe(self, audio: bytes) -> str:
        return _FAKE_TEXTO


@lru_cache
def get_transcriber() -> Transcriber:
    s = get_settings()
    if s.whisper_backend == "real":
        return RealTranscriber(s.whisper_model)
    return FakeTranscriber()
