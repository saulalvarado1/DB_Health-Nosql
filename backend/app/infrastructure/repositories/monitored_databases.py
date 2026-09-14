from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.persistence.models import DatabaseEngine, MonitoredDatabase


class MonitoredDatabaseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_engine(self, engine_id: str) -> DatabaseEngine | None:
        return self._session.get(DatabaseEngine, engine_id)

    def add(self, monitored_database: MonitoredDatabase) -> MonitoredDatabase:
        self._session.add(monitored_database)
        return monitored_database

    def get_for_owner(self, database_id: UUID, owner_id: UUID) -> MonitoredDatabase | None:
        statement = (
            select(MonitoredDatabase)
            .options(selectinload(MonitoredDatabase.schedule))
            .where(
                MonitoredDatabase.id == database_id,
                MonitoredDatabase.owner_id == owner_id,
            )
        )
        return self._session.scalar(statement)

    def list_for_owner(self, owner_id: UUID) -> list[MonitoredDatabase]:
        statement = (
            select(MonitoredDatabase)
            .options(selectinload(MonitoredDatabase.schedule))
            .where(MonitoredDatabase.owner_id == owner_id)
            .order_by(MonitoredDatabase.created_at.desc())
        )
        return list(self._session.scalars(statement))
