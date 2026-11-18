import httpx
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session
from app.api.schemas.authentication import (
    AccessTokenResponse,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.core.config import settings
from app.core.security import create_access_token
from app.domain.commands import RegisterUserCommand
from app.domain.errors import AuthenticationError
from app.infrastructure.persistence.models import User
from app.services.authentication import AuthenticationService

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    session: Session = Depends(get_session),
) -> UserResponse:
    user = AuthenticationService(session).register(
        RegisterUserCommand(email=str(request.email), password=request.password)
    )
    return UserResponse.model_validate(user)


@router.post("/login", response_model=AccessTokenResponse)
def login(request: LoginRequest, session: Session = Depends(get_session)) -> AccessTokenResponse:
    user = AuthenticationService(session).authenticate(str(request.email), request.password)
    return AccessTokenResponse(access_token=create_access_token(user.id))


@router.post("/google", response_model=AccessTokenResponse)
def login_with_google(
    request: GoogleLoginRequest,
    session: Session = Depends(get_session),
) -> AccessTokenResponse:
    credential = request.credential.strip()
    if not credential:
        raise AuthenticationError("El token de Google no puede estar vacío.")

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": credential},
            )
    except Exception as err:
        raise AuthenticationError(f"Error de red al conectar con Google: {err}") from err

    if resp.status_code != 200:
        raise AuthenticationError("Token de Google inválido o expirado.")

    payload = resp.json()
    email = payload.get("email")
    email_verified = payload.get("email_verified")
    if not email or str(email_verified).lower() not in {"true", "1"}:
        raise AuthenticationError("El correo de Google no está verificado.")

    if settings.google_client_id:
        token_aud = payload.get("aud")
        if token_aud != settings.google_client_id:
            raise AuthenticationError("El token de Google no coincide con el cliente configurado.")

    user = AuthenticationService(session).authenticate_or_register_google(email)
    return AccessTokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
