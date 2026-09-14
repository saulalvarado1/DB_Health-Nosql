from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.infrastructure.persistence.models import (
    MetricSample,
    MetricValue,
    MonitoredDatabase,
)


class MonitoringHistoryRepository:
    """Consulta muestras históricas sin romper el aislamiento por propietario."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_database_and_owner(
        self, *, database_id: UUID, owner_id: UUID, limit: int
    ) -> list[MetricSample]:
        statement = (
            select(MetricSample)
            .join(MonitoredDatabase)
            .options(
                joinedload(MetricSample.health_assessment),
                selectinload(MetricSample.values).joinedload(MetricValue.metric_definition),
            )
            .where(
                MetricSample.monitored_database_id == database_id,
                MonitoredDatabase.owner_id == owner_id,
            )
            .order_by(MetricSample.collected_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(statement))
