from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.errors import ConfigurationError, ResourceConflictError, ResourceNotFoundError
from app.infrastructure.persistence.models import ThresholdProfile, ThresholdRule
from app.infrastructure.repositories.monitored_databases import MonitoredDatabaseRepository
from app.infrastructure.repositories.thresholds import ThresholdProfileRepository


def validate_threshold_pair(direction: str, warning_value: float, critical_value: float) -> None:
    """Garantiza que warning ocurra antes que critical para cada dirección."""
    if direction == "above" and warning_value >= critical_value:
        raise ConfigurationError(
            "Para una métrica ascendente, warning debe ser menor que critical."
        )
    if direction == "below" and warning_value <= critical_value:
        raise ConfigurationError(
            "Para una métrica descendente, warning debe ser mayor que critical."
        )
    if direction not in {"above", "below"}:
        raise ConfigurationError("La métrica tiene una dirección de alerta no válida.")


class ThresholdManagementService:
    """Consulta y personaliza umbrales de una instancia sin afectar a las demás."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._databases = MonitoredDatabaseRepository(session)
        self._profiles = ThresholdProfileRepository(session)

    def get_for_owner(self, *, database_id: UUID, owner_id: UUID) -> ThresholdProfile:
        profile = self._profiles.get_assigned_for_database_and_owner(database_id, owner_id)
        if profile is None:
            raise ResourceNotFoundError("No se encontró el perfil de umbrales de la instancia.")
        return profile

    def update_rule(
        self,
        *,
        database_id: UUID,
        owner_id: UUID,
        metric_code: str,
        warning_value: float,
        critical_value: float,
    ) -> ThresholdProfile:
        monitored_database = self._databases.get_for_owner(database_id, owner_id)
        if monitored_database is None:
            raise ResourceNotFoundError("No se encontró la instancia monitoreada.")

        profile = self.get_for_owner(database_id=database_id, owner_id=owner_id)
        definition = self._profiles.get_enabled_metric_for_engine(
            monitored_database.engine_id, metric_code
        )
        if definition is None:
            raise ResourceNotFoundError("No existe esa métrica para el motor de la instancia.")
        validate_threshold_pair(definition.alert_direction, warning_value, critical_value)

        if profile.is_default:
            profile = self._profiles.clone_for_database(profile, monitored_database)

        rule = next(
            (item for item in profile.rules if item.metric_definition_id == definition.id),
            None,
        )
        if rule is None:
            profile.rules.append(
                ThresholdRule(
                    metric_definition_id=definition.id,
                    warning_value=warning_value,
                    critical_value=critical_value,
                )
            )
        else:
            rule.warning_value = warning_value
            rule.critical_value = critical_value

        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise ResourceConflictError("No fue posible guardar el perfil de umbrales.") from error
        refreshed_profile = self.get_for_owner(database_id=database_id, owner_id=owner_id)
        return refreshed_profile
