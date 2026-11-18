"""Pruebas unitarias para autenticación y registro con Google."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_session
from app.core.config import settings
from app.domain.errors import AuthenticationError
from app.infrastructure.persistence.models import User
from app.main import create_application
from app.services.authentication import AuthenticationService


def test_authenticate_or_register_google_new_user() -> None:
    session = MagicMock()
    service = AuthenticationService(session)

    # Mock user repository
    service._users = MagicMock()
    service._users.get_by_email.return_value = None

    with patch("app.services.authentication.ThresholdProfileRepository") as mock_profile_repo:
        user = service.authenticate_or_register_google("nuevo.usuario@example.com")

        assert user.email == "nuevo.usuario@example.com"
        assert user.password_hash is not None
        service._users.add.assert_called_once_with(user)
        session.flush.assert_called_once()
        mock_profile_repo.return_value.create_defaults_for_user.assert_called_once_with(user.id)
        session.commit.assert_called_once()
        session.refresh.assert_called_once_with(user)


def test_authenticate_or_register_google_existing_active_user() -> None:
    session = MagicMock()
    service = AuthenticationService(session)

    existing_user = User(
        id=uuid4(),
        email="existente@example.com",
        password_hash="argon2id$mockhash",
        is_active=True,
    )
    service._users = MagicMock()
    service._users.get_by_email.return_value = existing_user

    user = service.authenticate_or_register_google("EXISTENTE@example.com")

    assert user == existing_user
    service._users.add.assert_not_called()
    session.commit.assert_not_called()


def test_authenticate_or_register_google_inactive_user_raises() -> None:
    session = MagicMock()
    service = AuthenticationService(session)

    inactive_user = User(
        id=uuid4(),
        email="inactivo@example.com",
        password_hash="argon2id$mockhash",
        is_active=False,
    )
    service._users = MagicMock()
    service._users.get_by_email.return_value = inactive_user

    with pytest.raises(AuthenticationError, match="desactivada"):
        service.authenticate_or_register_google("inactivo@example.com")


def test_google_login_route_success(monkeypatch) -> None:
    user_id = uuid4()
    mock_user = User(
        id=user_id,
        email="google.user@example.com",
        password_hash="argon2id$mockhash",
        is_active=True,
    )

    mock_session = MagicMock()
    app = create_application()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "email": "google.user@example.com",
        "email_verified": "true",
        "aud": "google-client-id-123",
    }

    with patch("httpx.Client") as mock_client_cls, \
         patch("app.services.authentication.AuthenticationService.authenticate_or_register_google") as mock_auth:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        mock_auth.return_value = mock_user

        client = TestClient(app)
        res = client.post("/api/v1/auth/google", json={"credential": "valid_token_xyz"})

        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


def test_google_login_route_invalid_token() -> None:
    mock_session = MagicMock()
    app = create_application()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"error_description": "Invalid Value"}

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = TestClient(app)
        res = client.post("/api/v1/auth/google", json={"credential": "bad_token"})

        assert res.status_code == 401
        assert "inválido o expirado" in res.json()["detail"]


def test_google_login_route_unverified_email() -> None:
    mock_session = MagicMock()
    app = create_application()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "email": "google.user@example.com",
        "email_verified": "false",
    }

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = TestClient(app)
        res = client.post("/api/v1/auth/google", json={"credential": "unverified_token"})

        assert res.status_code == 401
        assert "no está verificado" in res.json()["detail"]


def test_google_login_route_client_id_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_client_id", "expected-client-id")
    mock_session = MagicMock()
    app = create_application()
    app.dependency_overrides[get_session] = lambda: mock_session

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "email": "google.user@example.com",
        "email_verified": "true",
        "aud": "wrong-client-id",
    }

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        client = TestClient(app)
        res = client.post("/api/v1/auth/google", json={"credential": "mismatched_token"})

        assert res.status_code == 401
        assert "no coincide con el cliente configurado" in res.json()["detail"]
