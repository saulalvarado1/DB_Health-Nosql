from collections.abc import Collection
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import Alert, MonitoredDatabase

ACTIVE_ALERT_STATUSES = ("open", "acknowledged")


class AlertRepository:
    """Consultas de alertas; mantiene el acceso SQL fuera de los servicios."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def open_or_update(
        self,
        *,
        monitored_database_id: UUID,
        sample_id: UUID,
        threshold_rule_id: UUID | None,
        deduplication_key: str,
        severity: str,
        message: str,
    ) -> Alert:
        active_alert = self._active_for_key(monitored_database_id, deduplication_key)
        if active_alert is None:
            alert = Alert(
                monitored_database_id=monitored_database_id,
                sample_id=sample_id,
                threshold_rule_id=threshold_rule_id,
                deduplication_key=deduplication_key,
                severity=severity,
                message=message,
            )
            self._session.add(alert)
            return alert

        active_alert.sample_id = sample_id
        active_alert.threshold_rule_id = threshold_rule_id
        active_alert.severity = severity
        active_alert.message = message
        return active_alert

    def resolve_absent(
        self,
        *,
        monitored_database_id: UUID,
        active_keys: Collection[str],
        resolved_at: datetime,
    ) -> None:
        statement = select(Alert).where(
            Alert.monitored_database_id == monitored_database_id,
            Alert.status.in_(ACTIVE_ALERT_STATUSES),
        )
        for alert in self._session.scalars(statement):
            if alert.deduplication_key not in active_keys:
                alert.status = "resolved"
                alert.resolved_at = resolved_at

    def list_active_for_database(self, monitored_database_id: UUID) -> list[Alert]:
        statement = select(Alert).where(
            Alert.monitored_database_id == monitored_database_id,
            Alert.status.in_(ACTIVE_ALERT_STATUSES),
        )
        return list(self._session.scalars(statement))

    def list_for_owner(self, owner_id: UUID, status_filter: str | None) -> list[Alert]:
        statement = (
            select(Alert)
            .join(MonitoredDatabase)
            .where(MonitoredDatabase.owner_id == owner_id)
            .order_by(Alert.created_at.desc())
        )
        if status_filter is not None:
            statement = statement.where(Alert.status == status_filter)
        return list(self._session.scalars(statement))

    def get_for_owner(self, alert_id: UUID, owner_id: UUID) -> Alert | None:
        statement = (
            select(Alert)
            .join(MonitoredDatabase)
            .where(Alert.id == alert_id, MonitoredDatabase.owner_id == owner_id)
        )
        return self._session.scalar(statement)

    def _active_for_key(self, monitored_database_id: UUID, deduplication_key: str) -> Alert | None:
        statement = select(Alert).where(
            Alert.monitored_database_id == monitored_database_id,
            Alert.deduplication_key == deduplication_key,
            Alert.status.in_(ACTIVE_ALERT_STATUSES),
        )
        return self._session.scalar(statement)
