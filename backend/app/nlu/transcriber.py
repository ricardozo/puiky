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


class RealTranscriber:
    def __init__(self, model_size: str) -> None:
        from faster_whisper import WhisperModel  # import perezoso

        # int8 en CPU: rápido y ligero, suficiente para notas de voz.
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio: bytes) -> str:
        segments, _ = self._model.transcribe(io.BytesIO(audio), language="es")
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
