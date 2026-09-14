from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.errors import ResourceNotFoundError
from app.infrastructure.persistence.models import MetricSample
from app.infrastructure.repositories.history import MonitoringHistoryRepository
from app.infrastructure.repositories.monitored_databases import MonitoredDatabaseRepository


class MonitoringHistoryService:
    """Obtiene el historial de una instancia después de verificar su propietario."""

    def __init__(self, session: Session) -> None:
        self._databases = MonitoredDatabaseRepository(session)
        self._history = MonitoringHistoryRepository(session)

    def list_for_owner(self, *, database_id: UUID, owner_id: UUID, limit: int) -> list[MetricSample]:
        database = self._databases.get_for_owner(database_id, owner_id)
        if database is None:
            raise ResourceNotFoundError("No se encontró la instancia monitoreada.")
        return self._history.list_for_database_and_owner(
            database_id=database_id,
            owner_id=owner_id,
            limit=limit,
        )
