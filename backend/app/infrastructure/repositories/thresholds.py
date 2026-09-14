from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    DatabaseThresholdProfile,
    MetricDefinition,
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
