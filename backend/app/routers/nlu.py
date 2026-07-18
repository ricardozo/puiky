"""Endpoints de la capa NLU: probar el tool calling sin Telegram.

`/interpret` procesa texto; `/transcribe` convierte audio a texto; `/voice`
encadena ambas (audio → texto → acciones), tal como hará el bot en la Fase 3.
"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.tenancy import get_tenant_db as get_db
from app.nlu.orchestrator import interpret
from app.nlu.transcriber import get_transcriber
from app.schemas.nlu import (
    AccionOut,
    InterpretRequest,
    InterpretResponse,
    TranscribeResponse,
    VoiceResponse,
)

router = APIRouter(prefix="/nlu", tags=["nlu"])


def _a_response(resultado) -> tuple[str, list[AccionOut]]:
    acciones = [
        AccionOut(tool=a.tool, argumentos=a.argumentos, resultado=a.resultado)
        for a in resultado.acciones
    ]
    return resultado.respuesta, acciones


@router.post("/interpret", response_model=InterpretResponse)
def interpretar(
    data: InterpretRequest, db: Session = Depends(get_db)
) -> InterpretResponse:
    """Interpreta texto en lenguaje natural y ejecuta las acciones."""
    respuesta, acciones = _a_response(
        interpret(db, data.texto, historial=data.historial)
    )
    return InterpretResponse(respuesta=respuesta, acciones=acciones)


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribir(file: UploadFile = File(...)) -> TranscribeResponse:
    """Transcribe un archivo de audio a texto (Whisper)."""
    audio = await file.read()
    return TranscribeResponse(texto=get_transcriber().transcribe(audio))


@router.post("/voice", response_model=VoiceResponse)
async def voz(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> VoiceResponse:
    """Audio → transcripción → interpretación con acciones (flujo del bot)."""
    audio = await file.read()
    texto = get_transcriber().transcribe(audio)
    respuesta, acciones = _a_response(interpret(db, texto))
    return VoiceResponse(texto=texto, respuesta=respuesta, acciones=acciones)
