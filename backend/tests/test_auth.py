"""Tests de seguridad (hash y JWT), sin BD."""

from app.auth.security import (
    crear_token,
    hash_password,
    verificar_token,
    verify_password,
)


def test_hash_roundtrip() -> None:
    h = hash_password("secreta123")
    assert h != "secreta123"  # nunca en claro
    assert verify_password("secreta123", h)
    assert not verify_password("otra", h)


def test_hash_es_salado() -> None:
    # Dos hashes de la misma clave difieren (salt aleatorio).
    assert hash_password("x") != hash_password("x")


def test_jwt_roundtrip() -> None:
    token = crear_token("admin")
    assert verificar_token(token) == "admin"


def test_jwt_invalido() -> None:
    assert verificar_token("no.es.un.jwt") is None
