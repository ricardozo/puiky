"""Schemas de autenticación."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    usuario: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    usuario: str


class PasswordChange(BaseModel):
    actual: str = Field(min_length=1)
    nueva: str = Field(min_length=6, max_length=100)
