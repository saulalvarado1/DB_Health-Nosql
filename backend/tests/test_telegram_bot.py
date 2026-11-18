"""Pruebas unitarias para el aislamiento multiusuario del TelegramBotListener."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.infrastructure.persistence.models import Alert, MonitoredDatabase
from app.services.telegram_bot import TelegramBotListener


def test_telegram_bot_help_reveals_user_chat_id() -> None:
    listener = TelegramBotListener(bot_token="test_token")
    mock_send = MagicMock()
    listener._send_response = mock_send  # type: ignore[method-assign]

    listener._cmd_help("123456789")

    mock_send.assert_called_once()
    called_chat_id = mock_send.call_args[0][0]
    called_text = mock_send.call_args[0][1]
    assert called_chat_id == "123456789"
    assert "123456789" in called_text
    assert "Tu Telegram Chat ID" in called_text


def test_telegram_bot_status_isolates_user_databases() -> None:
    listener = TelegramBotListener(bot_token="test_token")
    mock_send = MagicMock()
    listener._send_response = mock_send  # type: ignore[method-assign]

    db_user_1 = MagicMock(spec=MonitoredDatabase)
    db_user_1.id = uuid4()
    db_user_1.name = "MongoDB_User1"
    db_user_1.engine_id = "mongodb"
    db_user_1.telegram_chat_id = "111111"

    db_user_2 = MagicMock(spec=MonitoredDatabase)
    db_user_2.id = uuid4()
    db_user_2.name = "Redis_User2"
    db_user_2.engine_id = "redis"
    db_user_2.telegram_chat_id = "222222"

    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.all.return_value = [
        db_user_1,
        db_user_2,
    ]
    mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
        None
    )

    listener._session_factory = MagicMock(return_value=mock_session)
    mock_session.__enter__.return_value = mock_session

    # Usuario 1 consulta /status con chat_id 111111
    listener._cmd_status("111111")
    mock_send.assert_called_once()
    status_text_1 = mock_send.call_args[0][1]
    assert "MongoDB_User1" in status_text_1
    assert "Redis_User2" not in status_text_1  # NO debe ver la de User 2

    # Usuario desconocido consulta /status con chat_id 999999
    mock_send.reset_mock()
    listener._cmd_status("999999")
    mock_send.assert_called_once()
    status_text_unknown = mock_send.call_args[0][1]
    assert "MongoDB_User1" not in status_text_unknown
    assert "Redis_User2" not in status_text_unknown
    assert "No tienes bases de datos vinculadas" in status_text_unknown
    assert "999999" in status_text_unknown


def test_telegram_bot_alerts_isolates_user_alerts() -> None:
    listener = TelegramBotListener(bot_token="test_token")
    mock_send = MagicMock()
    listener._send_response = mock_send  # type: ignore[method-assign]

    db_user_1 = MagicMock(spec=MonitoredDatabase)
    db_user_1.id = uuid4()
    db_user_1.name = "MongoDB_User1"
    db_user_1.telegram_chat_id = "111111"

    alert_1 = MagicMock(spec=Alert)
    alert_1.severity = "critical"
    alert_1.message = "Alerta crítica de User 1"
    alert_1.monitored_database = db_user_1

    mock_session = MagicMock()
    # Primera query para dbs (filter().all())
    mock_session.query.return_value.filter.return_value.all.return_value = [db_user_1]
    # Segunda query para alerts (filter().order_by().limit().all())
    mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        alert_1
    ]

    listener._session_factory = MagicMock(return_value=mock_session)
    mock_session.__enter__.return_value = mock_session

    listener._cmd_alerts("111111")
    mock_send.assert_called_once()
    alert_text = mock_send.call_args[0][1]
    assert "MongoDB_User1" in alert_text
    assert "Alerta crítica de User 1" in alert_text
