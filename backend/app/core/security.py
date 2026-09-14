from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings
from app.domain.errors import AuthenticationError

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def access_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)


def create_access_token(user_id: UUID) -> str:
    payload = {"sub": str(user_id), "exp": access_token_expiry()}
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        return UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError) as error:
        raise AuthenticationError("El token de acceso no es válido.") from error
