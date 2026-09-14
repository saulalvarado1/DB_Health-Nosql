from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session
from app.api.schemas.authentication import (
    AccessTokenResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.core.security import create_access_token
from app.domain.commands import RegisterUserCommand
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


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
