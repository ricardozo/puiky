"""Schemas Pydantic de la capa NLU."""

from typing import Any

from pydantic import BaseModel, Field


class Mensaje(BaseModel):
    rol: str  # "user" | "assistant"
    texto: str


class InterpretRequest(BaseModel):
    texto: str = Field(min_length=1)
    # Turnos previos de la conversación (memoria), del más viejo al más nuevo.
    historial: list[Mensaje] = []


class AccionOut(BaseModel):
    tool: str
    argumentos: dict[str, Any]
    resultado: dict[str, Any]


class InterpretResponse(BaseModel):
    respuesta: str
    acciones: list[AccionOut] = []


class TranscribeResponse(BaseModel):
    texto: str


class VoiceResponse(InterpretResponse):
    texto: str  # lo que se transcribió del audio
