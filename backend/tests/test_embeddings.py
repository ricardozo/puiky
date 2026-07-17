"""Tests del backend 'fake' de embeddings: no requieren BD ni torch,
corren al instante (útiles para CI). El backend 'real' se valida a mano."""

from app.embeddings import FakeEmbedder


def test_dimension_correcta() -> None:
    emb = FakeEmbedder(dim=768)
    assert len(emb.embed_document("hola")) == 768
    assert len(emb.embed_query("hola")) == 768


def test_es_determinista() -> None:
    emb = FakeEmbedder(dim=768)
    assert emb.embed_document("misma nota") == emb.embed_document("misma nota")


def test_documento_y_consulta_difieren() -> None:
    # e5 (y este stub) prefijan distinto documento y consulta.
    emb = FakeEmbedder(dim=768)
    assert emb.embed_document("texto") != emb.embed_query("texto")


def test_vector_normalizado() -> None:
    emb = FakeEmbedder(dim=768)
    vec = emb.embed_document("cualquier cosa")
    norma = sum(v * v for v in vec) ** 0.5
    assert abs(norma - 1.0) < 1e-6
