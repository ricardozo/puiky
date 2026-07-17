"""Servicio de embeddings para la búsqueda semántica.

Interfaz intercambiable con dos backends, elegidos por `EMBED_BACKEND`:

- "real": modelo local `multilingual-e5-base` (sentence-transformers). Es el
  que corre en producción (Ubuntu). e5 exige prefijar el texto con
  "query:" (consultas) o "passage:" (documentos guardados), y se usa
  distancia coseno, por eso los vectores se normalizan.
- "fake": vector determinista derivado de un hash, sin cargar torch. Sirve
  para tests/CI y para arrancar al instante durante el desarrollo. No mide
  significado real, solo es estable y reproducible.

El resto de la app depende de la interfaz `Embedder`, nunca del backend
concreto: cambiar de uno a otro es cambiar una variable de entorno.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Protocol

from app.config import get_settings


class Embedder(Protocol):
    """Contrato común. Notas y consultas se vectorizan distinto (e5)."""

    def embed_document(self, text: str) -> list[float]: ...

    def embed_query(self, text: str) -> list[float]: ...


class E5Embedder:
    """Backend real: multilingual-e5-base vía sentence-transformers."""

    def __init__(self, model_name: str) -> None:
        # Import perezoso: solo se carga torch cuando este backend se usa.
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def _encode(self, text: str) -> list[float]:
        vector = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_document(self, text: str) -> list[float]:
        return self._encode(f"passage: {text}")

    def embed_query(self, text: str) -> list[float]:
        return self._encode(f"query: {text}")


class FakeEmbedder:
    """Backend de prueba: vector determinista, normalizado, sin dependencias."""

    def __init__(self, dim: int) -> None:
        self._dim = dim

    def _encode(self, text: str) -> list[float]:
        # Deriva `dim` floats en [-1, 1) de forma reproducible desde el hash.
        raw = bytearray()
        counter = 0
        while len(raw) < self._dim * 4:
            raw += hashlib.sha256(f"{text}:{counter}".encode()).digest()
            counter += 1
        values = [
            int.from_bytes(raw[i : i + 4], "big") / 2**31 - 1.0
            for i in range(0, self._dim * 4, 4)
        ]
        norm = sum(v * v for v in values) ** 0.5 or 1.0
        return [v / norm for v in values]

    def embed_document(self, text: str) -> list[float]:
        return self._encode(f"passage: {text}")

    def embed_query(self, text: str) -> list[float]:
        return self._encode(f"query: {text}")


@lru_cache
def get_embedder() -> Embedder:
    """Devuelve el embedder según el entorno. Cacheado: el modelo real se
    carga una sola vez por proceso."""
    settings = get_settings()
    if settings.embed_backend == "fake":
        return FakeEmbedder(settings.embedding_dim)
    return E5Embedder(settings.embedding_model)
