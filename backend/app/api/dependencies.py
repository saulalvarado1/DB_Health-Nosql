from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.security import decode_access_token
from app.domain.errors import AuthenticationError
from app.infrastructure.persistence.models import User
from app.infrastructure.repositories.users import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_session() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere un token de acceso.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = decode_access_token(credentials.credentials)
    except AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de acceso no es válido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user = UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario de este token no está disponible.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
