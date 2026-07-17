"""Cliente HTTP a la API de Puiky (capa NLU). El bot no habla con la BD.

Se autentica ante la API con el token de servicio (llamante interno de
confianza), enviado como `Authorization: Bearer <service_token>`.
"""

from __future__ import annotations

import httpx

# El LLM real (Qwen) puede tardar; damos margen amplio.
_TIMEOUT = httpx.Timeout(300.0)


class PuikyClient:
    def __init__(self, base_url: str, service_token: str = "") -> None:
        self._base = base_url.rstrip("/")
        self._headers = (
            {"Authorization": f"Bearer {service_token}"} if service_token else {}
        )

    async def interpret(self, texto: str) -> dict:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(
                f"{self._base}/nlu/interpret",
                json={"texto": texto},
                headers=self._headers,
            )
            r.raise_for_status()
            return r.json()

    async def voice(self, audio: bytes, filename: str = "voz.ogg") -> dict:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            files = {"file": (filename, audio, "audio/ogg")}
            r = await c.post(
                f"{self._base}/nlu/voice", files=files, headers=self._headers
            )
            r.raise_for_status()
            return r.json()
