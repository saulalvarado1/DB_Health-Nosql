from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.models import HealthStatus
from app.services.alerts import AlertLifecycleService, AlertSignal


class RecordingAlertRepository:
    def __init__(self) -> None:
        self.opened: list[dict[str, object]] = []
        self.resolved: list[dict[str, object]] = []

    def open_or_update(self, **kwargs: object) -> None:
        self.opened.append(kwargs)

    def resolve_absent(self, **kwargs: object) -> None:
        self.resolved.append(kwargs)


def test_lifecycle_keeps_only_current_alert_keys_active() -> None:
    repository = RecordingAlertRepository()
    service = AlertLifecycleService(repository)
    database_id = uuid4()
    sample_id = uuid4()
    rule_id = uuid4()
    evaluated_at = datetime(2026, 9, 14, 12, 30, tzinfo=UTC)

    service.synchronize(
        monitored_database_id=database_id,
        sample_id=sample_id,
        signals=(
            AlertSignal(
                deduplication_key=f"threshold-rule:{rule_id}",
                severity=HealthStatus.WARNING,
                message="Uso de memoria alcanzó un nivel warning.",
                threshold_rule_id=rule_id,
            ),
        ),
        evaluated_at=evaluated_at,
    )

    assert repository.opened == [
        {
            "monitored_database_id": database_id,
            "sample_id": sample_id,
            "threshold_rule_id": rule_id,
            "deduplication_key": f"threshold-rule:{rule_id}",
            "severity": "warning",
            "message": "Uso de memoria alcanzó un nivel warning.",
        }
    ]
    assert repository.resolved == [
        {
            "monitored_database_id": database_id,
            "active_keys": {f"threshold-rule:{rule_id}"},
            "resolved_at": evaluated_at,
        }
    ]


def test_lifecycle_rejects_a_non_alert_health_status() -> None:
    service = AlertLifecycleService(RecordingAlertRepository())

    with pytest.raises(ValueError, match="warning o critical"):
        service.synchronize(
            monitored_database_id=uuid4(),
            sample_id=uuid4(),
            signals=(
                AlertSignal(
                    deduplication_key="not-an-alert",
                    severity=HealthStatus.HEALTHY,
                    message="No debería abrirse.",
                    threshold_rule_id=None,
                ),
            ),
            evaluated_at=datetime(2026, 9, 14, 12, 30, tzinfo=UTC),
        )
