"""Endpoints de autenticación."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import require_auth
from app.auth.security import crear_token, verify_password
from app.database import get_db
from app.models.users import User
from app.schemas.auth import LoginRequest, MeResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Valida usuario/contraseña y devuelve un JWT de sesión."""
    user = db.execute(
        select(User).where(User.usuario == data.usuario)
    ).scalar_one_or_none()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Usuario o contraseña incorrectos"
        )
    return TokenResponse(access_token=crear_token(user.usuario))


@router.get("/me", response_model=MeResponse)
def me(principal: str = Depends(require_auth)) -> MeResponse:
    """Devuelve quién es el llamante autenticado (para el frontend)."""
    return MeResponse(usuario=principal)
