"""Servicio de notificaciones en tiempo real a Telegram para alertas de bases de datos."""

import html
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.core.secrets import CredentialsCipher
from app.domain.errors import ConfigurationError
from app.infrastructure.persistence.models import MonitoredDatabase

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


@dataclass(frozen=True, slots=True)
class TelegramDeliveryResult:
    delivered: bool
    status_code: int | None = None
    error_message: str | None = None


class TelegramNotificationService:
    """Envía notificaciones de alerta y salud a través de la API de Telegram."""

    def __init__(
        self,
        cipher: CredentialsCipher | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._cipher = cipher or CredentialsCipher()
        self._http_client = http_client

    def resolve_bot_token(self, database: MonitoredDatabase | None = None) -> str | None:
        """Obtiene el bot token específico de la base de datos o el predeterminado del sistema."""
        if database is not None and database.telegram_bot_token_encrypted:
            try:
                return self._cipher.decrypt(database.telegram_bot_token_encrypted)
            except (ValueError, TypeError):
                logger.warning("No fue posible descifrar el token de Telegram personalizado.")
                return None

        if settings.telegram_bot_token is not None:
            return settings.telegram_bot_token.get_secret_value()

        return None

    def send_message(
        self,
        bot_token: str,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
    ) -> TelegramDeliveryResult:
        """Envía un mensaje directo a Telegram via HTTP POST."""
        clean_token = bot_token.strip()
        clean_chat_id = chat_id.strip()
        if not clean_token:
            return TelegramDeliveryResult(delivered=False, error_message="Token de bot no configurado.")
        if not clean_chat_id:
            return TelegramDeliveryResult(delivered=False, error_message="Chat ID no configurado.")

        url = f"{TELEGRAM_API_BASE}/bot{clean_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": clean_chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            if self._http_client is not None:
                response = self._http_client.post(url, json=payload, timeout=10.0)
            else:
                with httpx.Client(timeout=10.0) as client:
                    response = client.post(url, json=payload)

            if response.status_code == 200:
                return TelegramDeliveryResult(delivered=True, status_code=200)

            try:
                data = response.json()
                description = data.get("description", response.text)
            except (ValueError, KeyError):
                description = response.text

            logger.warning(
                "Error en Telegram API al enviar notificación. Código %s: %s",
                response.status_code,
                description,
            )
            return TelegramDeliveryResult(
                delivered=False,
                status_code=response.status_code,
                error_message=f"Telegram API respondió con error ({response.status_code}): {description}",
            )
        except Exception as error:  # noqa: BLE001 - Notification delivery failure must not crash monitoring.
            logger.warning("Excepción de red al enviar mensaje a Telegram: %s", error)
            return TelegramDeliveryResult(
                delivered=False,
                error_message=f"No se pudo conectar con los servidores de Telegram: {error}",
            )

    def send_test_notification(
        self,
        database: MonitoredDatabase,
        custom_chat_id: str | None = None,
        custom_bot_token: str | None = None,
    ) -> TelegramDeliveryResult:
        """Envía un mensaje de prueba para validar que el bot y chat_id funcionen."""
        token = custom_bot_token or self.resolve_bot_token(database)
        chat_id = custom_chat_id or database.telegram_chat_id

        if not token:
            raise ConfigurationError(
                "No hay un Bot Token de Telegram configurado (ni en la base de datos ni en el sistema)."
            )
        if not chat_id:
            raise ConfigurationError(
                "Debes ingresar un Chat ID de Telegram para realizar la prueba."
            )

        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        message = (
            "🤖 <b>DB Health Monitor — Notificación de Prueba</b>\n\n"
            f"✅ ¡Conexión con Telegram verificada exitosamente!\n\n"
            f"<b>Base de Datos:</b> <code>{html.escape(database.name)}</code>\n"
            f"<b>Motor:</b> {html.escape(database.engine_id.upper())}\n"
            f"<b>Fecha:</b> {now_str}\n\n"
            "<i>Recibirás alertas en este chat cuando el estado de tu base de datos cambie según las reglas configuradas.</i>"
        )
        return self.send_message(bot_token=token, chat_id=chat_id, text=message)

    def notify_alert_event(
        self,
        database: MonitoredDatabase,
        *,
        event_type: str,  # 'warning', 'critical', 'recovery'
        message: str,
        health_score: int,
        health_status: str,
    ) -> TelegramDeliveryResult | None:
        """Evalúa si la base de datos tiene habilitada la notificación y envía el aviso."""
        if not database.telegram_notifications_enabled or not database.telegram_chat_id:
            return None

        if event_type == "warning" and not database.notify_on_warning:
            return None
        if event_type == "critical" and not database.notify_on_critical:
            return None
        if event_type == "recovery" and not database.notify_on_recovery:
            return None

        bot_token = self.resolve_bot_token(database)
        if not bot_token:
            logger.warning(
                "Notificaciones activadas para %s pero no se encontró un bot token válido.",
                database.id,
            )
            return None

        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        escaped_name = html.escape(database.name)
        escaped_engine = html.escape(database.engine_id.upper())
        escaped_msg = html.escape(message)

        if event_type == "critical":
            header = "🚨 <b>ALERTA CRÍTICA: DB Health Monitor</b>"
            status_text = "🔴 CRÍTICO"
        elif event_type == "warning":
            header = "⚠️ <b>ADVERTENCIA: DB Health Monitor</b>"
            status_text = "🟡 ADVERTENCIA"
        else:
            header = "✅ <b>RECUPERACIÓN: DB Health Monitor</b>"
            status_text = "🟢 SALUDABLE"

        text = (
            f"{header}\n\n"
            f"<b>Base de Datos:</b> <code>{escaped_name}</code> ({escaped_engine})\n"
            f"<b>Estado:</b> {status_text} (Score: <b>{health_score}/100</b>)\n"
            f"<b>Detalle:</b> {escaped_msg}\n"
            f"<b>Fecha:</b> {now_str}"
        )

        return self.send_message(bot_token=bot_token, chat_id=database.telegram_chat_id, text=text)
