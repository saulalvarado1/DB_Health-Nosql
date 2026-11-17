"""Servicio interactivo de Telegram Bot para comandos /status, /alerts, /ping y botones."""

from __future__ import annotations

import html
import logging
import threading
import time
from typing import Any
from uuid import UUID

import httpx

from app.core.database import SessionLocal
from app.infrastructure.persistence.models import (
    Alert,
    HealthAssessment,
    MetricSample,
    MonitoredDatabase,
)

logger = logging.getLogger(__name__)
TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramBotListener:
    """Escucha comandos de usuarios en Telegram y responde en tiempo real."""

    def __init__(self, bot_token: str, session_factory=SessionLocal) -> None:
        self._bot_token = bot_token.strip()
        self._session_factory = session_factory
        self._last_update_id = 0
        self._is_running = False
        self._thread: threading.Thread | None = None

    def start_background(self) -> None:
        """Inicia el escucha interactivo en un hilo en segundo plano."""
        if not self._bot_token:
            logger.info("Telegram Bot Listener omitido: token no configurado.")
            return

        if self._is_running:
            return

        self._is_running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="TelegramBotListener"
        )
        self._thread.start()
        logger.info("Telegram Bot Listener interactivo iniciado en segundo plano.")

    def stop(self) -> None:
        self._is_running = False

    def _run_loop(self) -> None:
        while self._is_running:
            try:
                self.poll_updates()
            except Exception as error:  # noqa: BLE001
                logger.debug("Error transitorio en Telegram polling: %s", error)
            time.sleep(2.0)

    def poll_updates(self) -> None:
        """Obtiene y procesa nuevos mensajes y clics de botones en Telegram."""
        url = f"{TELEGRAM_API_BASE}/bot{self._bot_token}/getUpdates"
        params = {"offset": self._last_update_id + 1, "timeout": 2}

        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(url, params=params)
                if res.status_code != 200:
                    return
                data = res.json()
        except Exception:  # noqa: BLE001
            return

        updates = data.get("result", [])
        for update in updates:
            self._last_update_id = max(self._last_update_id, update.get("update_id", 0))

            if "message" in update:
                self._handle_message(update["message"])
            elif "callback_query" in update:
                self._handle_callback_query(update["callback_query"])

    def _send_response(
        self,
        chat_id: int | str,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> None:
        url = f"{TELEGRAM_API_BASE}/bot{self._bot_token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        try:
            with httpx.Client(timeout=5.0) as client:
                client.post(url, json=payload)
        except Exception as err:  # noqa: BLE001
            logger.warning("Fallo al responder mensaje en Telegram: %s", err)

    def _answer_callback_query(self, callback_query_id: str, text: str) -> None:
        url = f"{TELEGRAM_API_BASE}/bot{self._bot_token}/answerCallbackQuery"
        try:
            with httpx.Client(timeout=5.0) as client:
                client.post(url, json={"callback_query_id": callback_query_id, "text": text})
        except Exception as err:  # noqa: BLE001
            logger.warning("Fallo al responder callback query en Telegram: %s", err)

    def _handle_message(self, message: dict[str, Any]) -> None:
        text = message.get("text", "").strip()
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        if not chat_id or not text:
            return

        command = text.split()[0].lower()

        if command in {"/start", "/help", "ayuda"}:
            self._cmd_help(chat_id)
        elif command in {"/status", "/estado", "estado"}:
            self._cmd_status(chat_id)
        elif command in {"/alerts", "/alertas", "alertas"}:
            self._cmd_alerts(chat_id)
        elif command in {"/ping", "ping"}:
            self._cmd_ping(chat_id)
        else:
            self._send_response(
                chat_id,
                "🤖 Comando no reconocido. Escribe <b>/status</b> para ver la salud de tus bases de datos o <b>/help</b> para ver comandos disponibles.",
            )

    def _cmd_help(self, chat_id: int | str) -> None:
        help_text = (
            "🤖 <b>DB Health Monitor — Asistente de Operaciones</b>\n\n"
            f"🔑 <b>Tu Telegram Chat ID:</b> <code>{chat_id}</code>\n\n"
            "Comandos disponibles en tiempo real:\n"
            "• <b>/status</b> — Consulta la salud, puntaje y estado de tus bases de datos vinculadas.\n"
            "• <b>/alerts</b> — Lista las alertas críticas o incidentes activos de tus bases de datos.\n"
            "• <b>/ping</b> — Comprueba la latencia del servidor de monitoreo.\n"
            "• <b>/help</b> — Muestra este menú de ayuda.\n\n"
            "<i>💡 Para vincular una base de datos a este chat, abre la plataforma web, ve a 'Configurar Telegram' en tu base de datos y pega tu Chat ID.</i>"
        )
        markup = {
            "inline_keyboard": [
                [
                    {"text": "📊 Ver Mi Estado (/status)", "callback_data": "cmd:status"},
                    {"text": "🚨 Ver Mis Alertas (/alerts)", "callback_data": "cmd:alerts"},
                ],
                [
                    {
                        "text": "🌐 Abrir Dashboard Web",
                        "url": "https://frontend-production-07c5.up.railway.app",
                    },
                ],
            ]
        }
        self._send_response(chat_id, help_text, reply_markup=markup)

    def _cmd_ping(self, chat_id: int | str) -> None:
        self._send_response(
            chat_id,
            "🏓 <b>PONG!</b>\n\nEl sistema <b>DB Health Monitor</b> está en línea y operando normalmente.",
        )

    def _cmd_status(self, chat_id: int | str) -> None:
        with self._session_factory() as session:
            str_chat_id = str(chat_id).strip()
            dbs = (
                session.query(MonitoredDatabase).filter(MonitoredDatabase.is_enabled.is_(True)).all()
            )

            user_dbs = [
                d for d in dbs
                if d.telegram_chat_id and str(d.telegram_chat_id).strip() == str_chat_id
            ]

            if not user_dbs:
                self._send_response(
                    chat_id,
                    "ℹ️ <b>No tienes bases de datos vinculadas a este chat de Telegram.</b>\n\n"
                    f"🔑 Tu Telegram Chat ID es: <code>{chat_id}</code>\n\n"
                    "<b>Para vincular tus bases de datos:</b>\n"
                    "1. Ingresa a la plataforma web con tu cuenta.\n"
                    "2. Entra al detalle de tu base de datos y haz clic en <b>Configurar Telegram</b>.\n"
                    f"3. Pega tu Chat ID: <code>{chat_id}</code> y activa las notificaciones.\n\n"
                    "Una vez guardado, escribe <b>/status</b> para monitorearlas desde aquí.",
                )
                return

            lines = ["📊 <b>ESTADO DE TUS BASES DE DATOS VINCULADAS:</b>\n"]
            for db in user_dbs:
                last_sample = (
                    session.query(MetricSample)
                    .filter(MetricSample.monitored_database_id == db.id)
                    .order_by(MetricSample.collected_at.desc())
                    .first()
                )

                score = 100
                status_icon = "🟢"
                status_label = "Saludable"

                if last_sample:
                    assessment = (
                        session.query(HealthAssessment)
                        .filter(HealthAssessment.metric_sample_id == last_sample.id)
                        .first()
                    )
                    if assessment:
                        score = assessment.score
                        if assessment.status == "critical":
                            status_icon = "🔴"
                            status_label = "Crítico"
                        elif assessment.status == "warning":
                            status_icon = "🟡"
                            status_label = "Advertencia"

                engine_icon = "🍃" if db.engine_id == "mongodb" else "⚡"
                lines.append(
                    f"{engine_icon} <b>{html.escape(db.name)}</b> ({db.engine_id.upper()})\n"
                    f"   Estado: {status_icon} <b>{score}/100</b> — {status_label}\n"
                )

            lines.append("<i>Actualizado en tiempo real por DB Health Monitor Engine.</i>")
            self._send_response(chat_id, "\n".join(lines))

    def _cmd_alerts(self, chat_id: int | str) -> None:
        with self._session_factory() as session:
            str_chat_id = str(chat_id).strip()
            dbs = (
                session.query(MonitoredDatabase).filter(MonitoredDatabase.is_enabled.is_(True)).all()
            )

            user_dbs = [
                d for d in dbs
                if d.telegram_chat_id and str(d.telegram_chat_id).strip() == str_chat_id
            ]

            if not user_dbs:
                self._send_response(
                    chat_id,
                    "ℹ️ <b>No tienes bases de datos vinculadas a este chat.</b>\n\n"
                    f"Tu Chat ID es: <code>{chat_id}</code>. Vincúlalo en la plataforma web para recibir y consultar alertas.",
                )
                return

            user_db_ids = [d.id for d in user_dbs]
            open_alerts = (
                session.query(Alert)
                .filter(Alert.status == "open", Alert.monitored_database_id.in_(user_db_ids))
                .order_by(Alert.created_at.desc())
                .limit(5)
                .all()
            )

            if not open_alerts:
                self._send_response(
                    chat_id,
                    "✅ <b>¡Sin incidentes activos!</b>\n\n"
                    "Todas tus bases de datos vinculadas están funcionando dentro de sus umbrales operativos normales.",
                )
                return

            lines = [f"🚨 <b>ALERTAS ABIERTAS DE TUS BASES DE DATOS ({len(open_alerts)}):</b>\n"]
            for alert in open_alerts:
                severity_icon = "🔴" if alert.severity == "critical" else "🟡"
                db_name = (
                    alert.monitored_database.name if alert.monitored_database else "BD Desconocida"
                )
                lines.append(
                    f"{severity_icon} <b>{html.escape(db_name)}</b>\n"
                    f"   Detalle: {html.escape(alert.message)}\n"
                    f"   Severidad: <code>{alert.severity.upper()}</code>\n"
                )

            lines.append(
                "<i>Puedes reconocerlas desde el panel web o respondiendo con los botones de acción.</i>"
            )
            self._send_response(chat_id, "\n".join(lines))

    def _handle_callback_query(self, query: dict[str, Any]) -> None:
        query_id = query.get("id")
        data = query.get("data", "")
        chat = query.get("message", {}).get("chat", {})
        chat_id = chat.get("id")

        if not query_id or not chat_id:
            return

        if data == "cmd:status":
            self._answer_callback_query(query_id, "Consultando estado...")
            self._cmd_status(chat_id)
        elif data == "cmd:alerts":
            self._answer_callback_query(query_id, "Buscando alertas...")
            self._cmd_alerts(chat_id)
        elif data.startswith("ack:"):
            db_id_str = data[4:]
            try:
                db_uuid = UUID(db_id_str)
                with self._session_factory() as session:
                    db = session.query(MonitoredDatabase).filter(MonitoredDatabase.id == db_uuid).first()
                    if not db or not db.telegram_chat_id or str(db.telegram_chat_id).strip() != str(chat_id).strip():
                        self._answer_callback_query(
                            query_id,
                            "No tienes permiso para gestionar esta base de datos.",
                        )
                        return

                    alerts = (
                        session.query(Alert)
                        .filter(Alert.monitored_database_id == db_uuid, Alert.status == "open")
                        .all()
                    )
                    count = len(alerts)
                    for a in alerts:
                        a.status = "acknowledged"
                    session.commit()

                self._answer_callback_query(
                    query_id,
                    f"¡{count} alerta(s) reconocida(s) con éxito!",
                )
                self._send_response(
                    chat_id,
                    "✅ <b>Incidente reconocido desde Telegram</b>\n\n"
                    "El DBA ha tomado conocimiento del incidente. Las alertas fueron marcadas como <code>acknowledged</code>.",
                )
            except Exception as err:  # noqa: BLE001
                self._answer_callback_query(query_id, f"Error: {err}")
