import json
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session
from app.api.presenters import monitored_database_response, monitoring_history_response
from app.api.schemas.monitored_databases import (
    CreateMonitoredDatabaseRequest,
    MonitoredDatabaseResponse,
    TelegramTestNotificationRequest,
    TelegramTestNotificationResponse,
    UpdateMonitoredDatabaseRequest,
)
from app.api.schemas.monitoring import MonitoringHistoryResponse, MonitoringRunResponse
from app.core.secrets import CredentialsCipher
from app.domain.commands import RegisterMonitoredDatabaseCommand, UpdateMonitoredDatabaseCommand
from app.domain.errors import ConfigurationError, ResourceNotFoundError
from app.infrastructure.connectors import build_connector_registry
from app.infrastructure.persistence.models import User
from app.infrastructure.repositories.monitored_databases import MonitoredDatabaseRepository
from app.services.database_registry import DatabaseRegistryService
from app.services.history import MonitoringHistoryService
from app.services.monitoring import MonitoringService
from app.services.notifications import TelegramNotificationService
from app.services.reports import ReportExportService

router = APIRouter(prefix="/databases")

RANGE_DELTAS: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}


@router.post("", response_model=MonitoredDatabaseResponse, status_code=status.HTTP_201_CREATED)
def create_monitored_database(
    request: CreateMonitoredDatabaseRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MonitoredDatabaseResponse:
    database = DatabaseRegistryService(session, CredentialsCipher()).register(
        current_user,
        RegisterMonitoredDatabaseCommand(
            name=request.name,
            engine_id=request.engine.value,
            connection_uri=request.connection_uri.get_secret_value(),
            interval_seconds=request.interval_seconds,
        ),
    )
    return monitored_database_response(database)


@router.get("", response_model=list[MonitoredDatabaseResponse])
def list_monitored_databases(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[MonitoredDatabaseResponse]:
    databases = MonitoredDatabaseRepository(session).list_for_owner(current_user.id)
    return [monitored_database_response(database) for database in databases]


@router.get("/{database_id}", response_model=MonitoredDatabaseResponse)
def get_monitored_database(
    database_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MonitoredDatabaseResponse:
    database = MonitoredDatabaseRepository(session).get_for_owner(database_id, current_user.id)
    if database is None:
        raise ResourceNotFoundError("No se encontró la instancia monitoreada.")
    return monitored_database_response(database)


@router.patch("/{database_id}", response_model=MonitoredDatabaseResponse)
def update_monitored_database(
    database_id: UUID,
    request: UpdateMonitoredDatabaseRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MonitoredDatabaseResponse:
    database = DatabaseRegistryService(session, CredentialsCipher()).update(
        database_id=database_id,
        owner_id=current_user.id,
        command=UpdateMonitoredDatabaseCommand(
            name=request.name,
            interval_seconds=request.interval_seconds,
            is_enabled=request.is_enabled,
            telegram_notifications_enabled=request.telegram_notifications_enabled,
            telegram_chat_id=request.telegram_chat_id,
            telegram_bot_token=(
                request.telegram_bot_token.get_secret_value()
                if request.telegram_bot_token is not None
                else None
            ),
            clear_telegram_bot_token=request.clear_telegram_bot_token,
            notify_on_warning=request.notify_on_warning,
            notify_on_critical=request.notify_on_critical,
            notify_on_recovery=request.notify_on_recovery,
        ),
    )
    return monitored_database_response(database)


@router.post("/{database_id}/telegram-test", response_model=TelegramTestNotificationResponse)
def test_telegram_notification(
    database_id: UUID,
    request: TelegramTestNotificationRequest | None = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> TelegramTestNotificationResponse:
    database = MonitoredDatabaseRepository(session).get_for_owner(database_id, current_user.id)
    if database is None:
        raise ResourceNotFoundError("No se encontró la instancia monitoreada.")

    custom_chat_id = request.chat_id.strip() if request and request.chat_id else None
    custom_bot_token = (
        request.bot_token.get_secret_value().strip()
        if request and request.bot_token
        else None
    )

    cipher = CredentialsCipher()
    service = TelegramNotificationService(cipher=cipher)
    result = service.send_test_notification(
        database=database,
        custom_chat_id=custom_chat_id,
        custom_bot_token=custom_bot_token,
    )
    if not result.delivered:
        raise ConfigurationError(
            result.error_message or "No fue posible entregar el mensaje de prueba a Telegram."
        )

    return TelegramTestNotificationResponse(
        success=True,
        message="Mensaje de prueba enviado exitosamente a Telegram.",
    )


@router.delete("/{database_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitored_database(
    database_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    DatabaseRegistryService(session, CredentialsCipher()).delete(
        database_id=database_id,
        owner_id=current_user.id,
    )


@router.get("/{database_id}/history", response_model=list[MonitoringHistoryResponse])
def list_monitoring_history(
    database_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    range: str | None = Query(default=None, pattern="^(1h|6h|24h|7d)$"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[MonitoringHistoryResponse]:
    since = datetime.now(UTC) - RANGE_DELTAS[range] if range in RANGE_DELTAS else None
    entries = MonitoringHistoryService(session).list_for_owner(
        database_id=database_id,
        owner_id=current_user.id,
        limit=limit,
        since=since,
    )
    return [monitoring_history_response(entry) for entry in entries]


@router.post("/{database_id}/collect", response_model=MonitoringRunResponse)
def collect_metrics_now(
    database_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MonitoringRunResponse:
    database = MonitoredDatabaseRepository(session).get_for_owner(database_id, current_user.id)
    if database is None:
        raise ResourceNotFoundError("No se encontró la instancia monitoreada.")
    result = MonitoringService(
        session=session,
        cipher=CredentialsCipher(),
        connectors=build_connector_registry(),
    ).collect_once(database)
    return MonitoringRunResponse.from_result(result)


@router.get("/{database_id}/export")
def export_health_report(
    database_id: UUID,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    range: str | None = Query(default=None, pattern="^(1h|6h|24h|7d)$"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    database = MonitoredDatabaseRepository(session).get_for_owner(database_id, current_user.id)
    if database is None:
        raise ResourceNotFoundError("No se encontró la instancia monitoreada.")

    since = datetime.now(UTC) - RANGE_DELTAS[range] if range in RANGE_DELTAS else None
    entries = MonitoringHistoryService(session).list_for_owner(
        database_id=database_id,
        owner_id=current_user.id,
        limit=limit,
        since=since,
    )
    report_service = ReportExportService(database, entries)
    slug = re.sub(r"[^a-zA-Z0-9_\-]+", "_", database.name).strip("_").lower() or "db"
    date_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    if format == "json":
        data = report_service.export_json()
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return Response(
            content=content,
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="reporte_salud_{slug}_{date_str}.json"'
            },
        )

    csv_content = report_service.export_csv()
    content_with_bom = "\ufeff" + csv_content
    return Response(
        content=content_with_bom,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="reporte_salud_{slug}_{date_str}.csv"'
        },
    )

