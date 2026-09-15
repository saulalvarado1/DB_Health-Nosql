from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.persistence.models import (
    DatabaseThresholdProfile,
    MetricDefinition,
    MonitoredDatabase,
    ThresholdProfile,
    ThresholdRule,
)

DEFAULT_RULES: dict[str, dict[str, tuple[float, float]]] = {
    "mongodb": {
        "availability": (0.5, 0.0),
    },
    "redis": {
        "availability": (0.5, 0.0),
        "memory_usage_percent": (80.0, 90.0),
    },
}


class ThresholdProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_defaults_for_user(self, owner_id: object) -> None:
        definitions = self._session.scalars(
            select(MetricDefinition).where(MetricDefinition.is_enabled.is_(True))
        )
        definitions_by_engine_and_code = {
            (definition.engine_id, definition.code): definition for definition in definitions
        }

        for engine_id, default_rules in DEFAULT_RULES.items():
            profile = ThresholdProfile(
                owner_id=owner_id,
                engine_id=engine_id,
                name="Predeterminado",
                is_default=True,
            )
            self._session.add(profile)
            self._session.flush()
            for metric_code, (warning_value, critical_value) in default_rules.items():
                definition = definitions_by_engine_and_code.get((engine_id, metric_code))
                if definition is not None:
                    profile.rules.append(
                        ThresholdRule(
                            metric_definition_id=definition.id,
                            warning_value=warning_value,
                            critical_value=critical_value,
                        )
                    )

    def get_default_for_owner_and_engine(
        self, owner_id: object, engine_id: str
    ) -> ThresholdProfile | None:
        statement = select(ThresholdProfile).where(
            ThresholdProfile.owner_id == owner_id,
            ThresholdProfile.engine_id == engine_id,
            ThresholdProfile.is_default.is_(True),
        )
        return self._session.scalar(statement)

    def rules_for_database(
        self, monitored_database_id: object
    ) -> list[tuple[ThresholdRule, MetricDefinition]]:
        statement = (
            select(ThresholdRule, MetricDefinition)
            .join(MetricDefinition, MetricDefinition.id == ThresholdRule.metric_definition_id)
            .join(ThresholdProfile, ThresholdProfile.id == ThresholdRule.profile_id)
            .join(
                DatabaseThresholdProfile,
                DatabaseThresholdProfile.threshold_profile_id == ThresholdProfile.id,
            )
            .where(DatabaseThresholdProfile.monitored_database_id == monitored_database_id)
        )
        return list(self._session.execute(statement).tuples())

    def get_assigned_for_database_and_owner(
        self, database_id: UUID, owner_id: UUID
    ) -> ThresholdProfile | None:
        statement = (
            select(ThresholdProfile)
            .join(
                DatabaseThresholdProfile,
                DatabaseThresholdProfile.threshold_profile_id == ThresholdProfile.id,
            )
            .join(
                MonitoredDatabase,
                MonitoredDatabase.id == DatabaseThresholdProfile.monitored_database_id,
            )
            .options(
                selectinload(ThresholdProfile.rules).selectinload(ThresholdRule.metric_definition)
            )
            .where(
                MonitoredDatabase.id == database_id,
                MonitoredDatabase.owner_id == owner_id,
            )
        )
        return self._session.scalar(statement)

    def get_enabled_metric_for_engine(
        self, engine_id: str, metric_code: str
    ) -> MetricDefinition | None:
        statement = select(MetricDefinition).where(
            MetricDefinition.engine_id == engine_id,
            MetricDefinition.code == metric_code,
            MetricDefinition.is_enabled.is_(True),
        )
        return self._session.scalar(statement)

    def clone_for_database(
        self, profile: ThresholdProfile, monitored_database: MonitoredDatabase
    ) -> ThresholdProfile:
        """Copia un perfil compartido antes de que una instancia lo personalice."""
        cloned_profile = ThresholdProfile(
            owner_id=profile.owner_id,
            engine_id=profile.engine_id,
            name=f"Personalizado {monitored_database.id}",
            is_default=False,
        )
        self._session.add(cloned_profile)
        self._session.flush()
        for rule in profile.rules:
            cloned_profile.rules.append(
                ThresholdRule(
                    metric_definition_id=rule.metric_definition_id,
                    warning_value=rule.warning_value,
                    critical_value=rule.critical_value,
                )
            )

        assignment = self._session.get(DatabaseThresholdProfile, monitored_database.id)
        if assignment is None:
            raise LookupError("La instancia no tiene un perfil de umbrales asignado.")
        assignment.threshold_profile_id = cloned_profile.id
        return cloned_profile

    def remove_if_unassigned(self, profile: ThresholdProfile) -> None:
        """Evita conservar perfiles personalizados sin ninguna instancia asignada."""
        if profile.is_default:
            return
        statement = select(DatabaseThresholdProfile.monitored_database_id).where(
            DatabaseThresholdProfile.threshold_profile_id == profile.id
        )
        if self._session.scalar(statement) is None:
            self._session.delete(profile)
