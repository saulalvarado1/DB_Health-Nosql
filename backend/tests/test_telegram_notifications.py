from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest

from app.api.presenters import monitored_database_response
from app.api.schemas.monitored_databases import UpdateMonitoredDatabaseRequest
from app.core.secrets import CredentialsCipher
from app.domain.errors import ConfigurationError
from app.infrastructure.persistence.models import MonitoredDatabase, MonitoringSchedule
from app.services.notifications import TelegramNotificationService


@pytest.fixture
def mock_cipher() -> CredentialsCipher:
    return CredentialsCipher(
        encryption_key="MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="
    )


def test_telegram_send_message_success() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    service = TelegramNotificationService(http_client=mock_client)
    result = service.send_message(
        bot_token="123456:ABC-DEF",
        chat_id="987654321",
        text="<b>Mensaje de prueba</b>",
    )

    assert result.delivered is True
    assert result.status_code == 200
    mock_client.post.assert_called_once()
    called_url = mock_client.post.call_args[0][0]
    called_json = mock_client.post.call_args[1]["json"]
    assert "123456:ABC-DEF" in called_url
    assert called_json["chat_id"] == "987654321"
    assert "Mensaje de prueba" in called_json["text"]


def test_telegram_send_message_api_error() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 400
    mock_response.json.return_value = {"ok": False, "description": "Bad Request: chat not found"}
    mock_response.text = '{"ok": false, "description": "Bad Request: chat not found"}'

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    service = TelegramNotificationService(http_client=mock_client)
    result = service.send_message(
        bot_token="123456:ABC-DEF",
        chat_id="invalid_chat",
        text="Texto",
    )

    assert result.delivered is False
    assert result.status_code == 400
    assert "chat not found" in result.error_message


def test_resolve_bot_token_from_database(mock_cipher: CredentialsCipher) -> None:
    encrypted_token = mock_cipher.encrypt("my-custom-bot-token-999")
    database = MonitoredDatabase(
        id=uuid4(),
        owner_id=uuid4(),
        engine_id="mongodb",
        name="Prod Mongo",
        connection_uri_encrypted="dummy",
        telegram_bot_token_encrypted=encrypted_token,
    )

    service = TelegramNotificationService(cipher=mock_cipher)
    token = service.resolve_bot_token(database)
    assert token == "my-custom-bot-token-999"


def test_notify_alert_event_respects_filter_toggles(mock_cipher: CredentialsCipher) -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = MagicMock(status_code=200)

    encrypted_token = mock_cipher.encrypt("token-123")
    database = MonitoredDatabase(
        id=uuid4(),
        owner_id=uuid4(),
        engine_id="redis",
        name="Cache Redis",
        connection_uri_encrypted="dummy",
        telegram_notifications_enabled=True,
        telegram_chat_id="112233",
        telegram_bot_token_encrypted=encrypted_token,
        notify_on_warning=False,
        notify_on_critical=True,
        notify_on_recovery=True,
    )

    service = TelegramNotificationService(cipher=mock_cipher, http_client=mock_client)

    # 1. Warning event should be ignored because notify_on_warning is False
    res_warning = service.notify_alert_event(
        database,
        event_type="warning",
        message="Memoria al 75%",
        health_score=70,
        health_status="warning",
    )
    assert res_warning is None
    assert mock_client.post.call_count == 0

    # 2. Critical event should be delivered
    res_critical = service.notify_alert_event(
        database,
        event_type="critical",
        message="Instancia no responde",
        health_score=0,
        health_status="critical",
    )
    assert res_critical is not None
    assert res_critical.delivered is True
    assert mock_client.post.call_count == 1
    assert "CRÍTICA" in mock_client.post.call_args[1]["json"]["text"]

    # 3. Recovery event should be delivered
    res_recovery = service.notify_alert_event(
        database,
        event_type="recovery",
        message="Alertas resueltas",
        health_score=100,
        health_status="healthy",
    )
    assert res_recovery is not None
    assert res_recovery.delivered is True
    assert mock_client.post.call_count == 2
    assert "RECUPERACIÓN" in mock_client.post.call_args[1]["json"]["text"]


def test_send_test_notification_requires_chat_id(mock_cipher: CredentialsCipher) -> None:
    encrypted_token = mock_cipher.encrypt("token-123")
    database = MonitoredDatabase(
        id=uuid4(),
        owner_id=uuid4(),
        engine_id="mongodb",
        name="DB Sin Chat",
        connection_uri_encrypted="dummy",
        telegram_notifications_enabled=True,
        telegram_chat_id=None,
        telegram_bot_token_encrypted=encrypted_token,
    )

    service = TelegramNotificationService(cipher=mock_cipher)
    with pytest.raises(ConfigurationError, match="Debes ingresar un Chat ID"):
        service.send_test_notification(database)


def test_monitored_database_response_masks_bot_token(mock_cipher: CredentialsCipher) -> None:
    database = MonitoredDatabase(
        id=uuid4(),
        owner_id=uuid4(),
        engine_id="mongodb",
        name="Test Database",
        connection_uri_encrypted="dummy",
        is_enabled=True,
        telegram_notifications_enabled=True,
        telegram_chat_id="12345",
        telegram_bot_token_encrypted=mock_cipher.encrypt("secret-bot-token"),
        notify_on_warning=True,
        notify_on_critical=True,
        notify_on_recovery=True,
    )
    database.schedule = MonitoringSchedule(interval_seconds=30)
    database.created_at = datetime.now(UTC)

    response = monitored_database_response(database)

    assert response.telegram_notifications_enabled is True
    assert response.telegram_chat_id == "12345"
    assert response.has_telegram_bot_token is True
    assert response.notify_on_warning is True
    assert not hasattr(response, "telegram_bot_token")  # Must never expose raw token!


def test_update_request_validation_accepts_telegram_changes() -> None:
    req = UpdateMonitoredDatabaseRequest(
        telegram_notifications_enabled=True,
        telegram_chat_id="998877",
    )
    assert req.telegram_notifications_enabled is True
    assert req.telegram_chat_id == "998877"
