from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.errors import ResourceNotFoundError
from app.infrastructure.persistence.models import MetricSample
from app.infrastructure.repositories.history import MonitoringHistoryRepository
from app.infrastructure.repositories.monitored_databases import MonitoredDatabaseRepository
from app.infrastructure.repositories.thresholds import ThresholdProfileRepository
from app.services.health_score import HealthRule
from app.services.metric_diagnostics import MetricDiagnostic, diagnose_metric


@dataclass(frozen=True, slots=True)
class MonitoringHistoryEntry:
    sample: MetricSample
    diagnostics: Mapping[str, MetricDiagnostic]


class MonitoringHistoryService:
    """Obtiene el historial de una instancia después de verificar su propietario."""

    def __init__(self, session: Session) -> None:
        self._databases = MonitoredDatabaseRepository(session)
        self._history = MonitoringHistoryRepository(session)
        self._thresholds = ThresholdProfileRepository(session)

    def list_for_owner(
        self,
        *,
        database_id: UUID,
        owner_id: UUID,
        limit: int,
        since: datetime | None = None,
    ) -> list[MonitoringHistoryEntry]:
        database = self._databases.get_for_owner(database_id, owner_id)
        if database is None:
            raise ResourceNotFoundError("No se encontró la instancia monitoreada.")
        samples = self._history.list_for_database_and_owner(
            database_id=database_id,
            owner_id=owner_id,
            limit=limit,
            since=since,
        )
        configured_rules = self._thresholds.rules_for_database(database_id)
        rules_by_code = {
            definition.code: HealthRule(
                metric_code=definition.code,
                display_name=definition.display_name,
                direction=definition.alert_direction,
                warning_value=float(rule.warning_value),
                critical_value=float(rule.critical_value),
            )
            for rule, definition in configured_rules
        }

        entries: list[MonitoringHistoryEntry] = []
        for index, sample in enumerate(samples):
            previous_values = (
                {
                    value.metric_definition.code: float(value.numeric_value)
                    for value in samples[index + 1].values
                }
                if index + 1 < len(samples)
                else {}
            )
            diagnostics = {
                value.metric_definition.code: diagnose_metric(
                    metric_code=value.metric_definition.code,
                    value=float(value.numeric_value),
                    rule=rules_by_code.get(value.metric_definition.code),
                    previous_value=previous_values.get(value.metric_definition.code),
                )
                for value in sample.values
            }
            entries.append(MonitoringHistoryEntry(sample=sample, diagnostics=diagnostics))
        return entries
