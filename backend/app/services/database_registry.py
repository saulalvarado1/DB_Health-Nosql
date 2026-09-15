from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.secrets import CredentialsCipher
from app.domain.commands import RegisterMonitoredDatabaseCommand, UpdateMonitoredDatabaseCommand
from app.domain.errors import ConfigurationError, ResourceConflictError, ResourceNotFoundError
from app.infrastructure.persistence.models import (
    DatabaseThresholdProfile,
    MonitoredDatabase,
    MonitoringSchedule,
    User,
)
from app.infrastructure.repositories.monitored_databases import MonitoredDatabaseRepository
from app.infrastructure.repositories.thresholds import ThresholdProfileRepository


class DatabaseRegistryService:
    """Registra instancias sin exponer ni guardar secretos en texto plano."""

    def __init__(self, session: Session, cipher: CredentialsCipher) -> None:
        self._session = session
        self._cipher = cipher
        self._databases = MonitoredDatabaseRepository(session)

    def register(
        self, owner: User, command: RegisterMonitoredDatabaseCommand
    ) -> MonitoredDatabase:
        engine = self._databases.get_engine(command.engine_id)
        if engine is None or not engine.is_enabled:
            raise ConfigurationError("El motor seleccionado no está disponible.")

        monitored_database = MonitoredDatabase(
            owner_id=owner.id,
            engine_id=engine.id,
            name=command.name.strip(),
            connection_uri_encrypted=self._cipher.encrypt(command.connection_uri),
        )
        monitored_database.schedule = MonitoringSchedule(interval_seconds=command.interval_seconds)
        default_profile = ThresholdProfileRepository(self._session).get_default_for_owner_and_engine(
            owner.id, engine.id
        )
        if default_profile is None:
            raise ConfigurationError("No existe un perfil de umbrales para este motor.")
        monitored_database.threshold_assignment = DatabaseThresholdProfile(
            threshold_profile_id=default_profile.id
        )
        self._databases.add(monitored_database)
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise ResourceConflictError(
                "Ya existe una instancia con ese nombre para el motor seleccionado."
            ) from error
        self._session.refresh(monitored_database)
        return monitored_database

    def update(
        self,
        *,
        database_id: UUID,
        owner_id: UUID,
        command: UpdateMonitoredDatabaseCommand,
    ) -> MonitoredDatabase:
        monitored_database = self._databases.get_for_owner(database_id, owner_id)
        if monitored_database is None:
            raise ResourceNotFoundError("No se encontró la instancia monitoreada.")
        if monitored_database.schedule is None:
            raise ConfigurationError("La instancia monitoreada no tiene programación configurada.")

        schedule_immediately = False
        if command.name is not None:
            monitored_database.name = command.name
        if command.interval_seconds is not None:
            monitored_database.schedule.interval_seconds = command.interval_seconds
            schedule_immediately = True
        if command.is_enabled is not None:
            monitored_database.is_enabled = command.is_enabled
            monitored_database.schedule.is_enabled = command.is_enabled
            schedule_immediately = command.is_enabled
        if schedule_immediately:
            monitored_database.schedule.next_run_at = datetime.now(UTC)

        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise ResourceConflictError(
                "Ya existe una instancia con ese nombre para el motor seleccionado."
            ) from error
        self._session.refresh(monitored_database)
        return monitored_database

    def delete(self, *, database_id: UUID, owner_id: UUID) -> None:
        monitored_database = self._databases.get_for_owner(database_id, owner_id)
        if monitored_database is None:
            raise ResourceNotFoundError("No se encontró la instancia monitoreada.")
        profile = ThresholdProfileRepository(self._session).get_assigned_for_database_and_owner(
            database_id, owner_id
        )
        self._databases.remove(monitored_database)
        self._session.flush()
        if profile is not None:
            ThresholdProfileRepository(self._session).remove_if_unassigned(profile)
        self._session.commit()
