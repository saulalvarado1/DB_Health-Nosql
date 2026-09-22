from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_session
from app.api.presenters import monitored_database_response, monitoring_history_response
from app.api.schemas.monitored_databases import (
    CreateMonitoredDatabaseRequest,
    MonitoredDatabaseResponse,
    UpdateMonitoredDatabaseRequest,
)
from app.api.schemas.monitoring import MonitoringHistoryResponse, MonitoringRunResponse
from app.core.secrets import CredentialsCipher
from app.domain.commands import RegisterMonitoredDatabaseCommand, UpdateMonitoredDatabaseCommand
from app.domain.errors import ResourceNotFoundError
from app.infrastructure.connectors import build_connector_registry
from app.infrastructure.persistence.models import User
from app.infrastructure.repositories.monitored_databases import MonitoredDatabaseRepository
from app.services.database_registry import DatabaseRegistryService
from app.services.history import MonitoringHistoryService
from app.services.monitoring import MonitoringService

router = APIRouter(prefix="/databases")


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
        ),
    )
    return monitored_database_response(database)


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
    limit: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[MonitoringHistoryResponse]:
    entries = MonitoringHistoryService(session).list_for_owner(
        database_id=database_id,
        owner_id=current_user.id,
        limit=limit,
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
