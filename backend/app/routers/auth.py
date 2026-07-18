"""Endpoints de autenticación (control, schema public)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import crear_token, verify_password
from app.models.users import User
from app.schemas.auth import LoginRequest, MeResponse, TokenResponse
from app.tenancy import Principal, get_control_db, get_tenant_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_control_db)) -> TokenResponse:
    """Valida usuario/contraseña y devuelve un JWT que lleva el inquilino."""
    user = db.execute(
        select(User).where(User.usuario == data.usuario)
    ).scalar_one_or_none()
    if (
        user is None
        or not user.activo
        or not verify_password(data.password, user.password_hash)
    ):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos"
        )
    return TokenResponse(
        access_token=crear_token(user.usuario, tenant=user.tenant_schema)
    )


@router.get("/me", response_model=MeResponse)
def me(db: Session = Depends(get_tenant_db)) -> MeResponse:
    """Devuelve quién es el llamante autenticado (para el frontend)."""
    principal: Principal = db.info["principal"]
    return MeResponse(usuario=principal.usuario)
