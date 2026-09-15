from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user
from app.api.presenters import monitored_database_response
from app.core.config import settings
from app.core.secrets import CredentialsCipher
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.domain.errors import AuthenticationError


def test_passwords_are_hashed_and_can_be_verified() -> None:
    password = "PruebaLocal2026!"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password("ClaveIncorrecta2026!", hashed_password)


def test_access_token_round_trip_returns_its_subject() -> None:
    user_id = uuid4()

    token = create_access_token(user_id)

    assert decode_access_token(token) == user_id


def test_expired_access_token_is_rejected() -> None:
    expired_token = jwt.encode(
        {"sub": str(uuid4()), "exp": datetime.now(UTC) - timedelta(seconds=1)},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(AuthenticationError, match="no es válido"):
        decode_access_token(expired_token)


def test_missing_or_malformed_bearer_credentials_are_rejected() -> None:
    with pytest.raises(HTTPException) as missing_token:
        get_current_user(credentials=None, session=object())

    assert missing_token.value.status_code == 401
    assert missing_token.value.detail == "Se requiere un token de acceso."

    with pytest.raises(HTTPException) as malformed_token:
        get_current_user(
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-jwt"),
            session=object(),
        )

    assert malformed_token.value.status_code == 401
    assert malformed_token.value.detail == "El token de acceso no es válido."


def test_connection_credentials_are_encrypted_before_storage() -> None:
    connection_uri = "redis://monitor:local-test-password@example.test:6379/0"
    cipher = CredentialsCipher()

    encrypted_uri = cipher.encrypt(connection_uri)

    assert encrypted_uri != connection_uri
    assert connection_uri not in encrypted_uri
    assert cipher.decrypt(encrypted_uri) == connection_uri


def test_tampered_encrypted_credentials_are_rejected() -> None:
    cipher = CredentialsCipher()
    encrypted_uri = cipher.encrypt("redis://example.test:6379/0")
    first_character = "A" if encrypted_uri[0] != "A" else "B"
    tampered_uri = f"{first_character}{encrypted_uri[1:]}"

    with pytest.raises(ValueError, match="No se pudo descifrar"):
        cipher.decrypt(tampered_uri)


def test_database_presenter_never_returns_connection_credentials() -> None:
    connection_uri = "redis://monitor:local-test-password@example.test:6379/0"
    database = SimpleNamespace(
        id=uuid4(),
        name="Redis de prueba",
        engine_id="redis",
        schedule=SimpleNamespace(interval_seconds=30),
        is_enabled=True,
        created_at=datetime(2026, 9, 14, tzinfo=UTC),
        connection_uri_encrypted=connection_uri,
    )

    response = monitored_database_response(database).model_dump()

    assert "connection_uri_encrypted" not in response
    assert connection_uri not in str(response)

