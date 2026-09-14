from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.errors import ResourceConflictError, ResourceNotFoundError
from app.domain.models import HealthStatus
from app.infrastructure.persistence.models import Alert
from app.infrastructure.repositories.alerts import AlertRepository


@dataclass(frozen=True, slots=True)
class AlertSignal:
    """Una condición actual que merece una alerta visible para el usuario."""

    deduplication_key: str
    severity: HealthStatus
    message: str
    threshold_rule_id: UUID | None


class AlertLifecycleRepository(Protocol):
    def open_or_update(
        self,
        *,
        monitored_database_id: UUID,
        sample_id: UUID,
        threshold_rule_id: UUID | None,
        deduplication_key: str,
        severity: str,
        message: str,
    ) -> Alert: ...

    def resolve_absent(
        self,
        *,
        monitored_database_id: UUID,
        active_keys: Collection[str],
        resolved_at: datetime,
    ) -> None: ...


class AlertLifecycleService:
    """Abre, actualiza o resuelve alertas al finalizar una evaluación."""

    def __init__(self, repository: AlertLifecycleRepository) -> None:
        self._repository = repository

    def synchronize(
        self,
        *,
        monitored_database_id: UUID,
        sample_id: UUID,
        signals: Iterable[AlertSignal],
        evaluated_at: datetime,
    ) -> None:
        active_keys: set[str] = set()
        for signal in signals:
            if signal.severity not in {HealthStatus.WARNING, HealthStatus.CRITICAL}:
                raise ValueError("Una alerta solo puede tener severidad warning o critical.")
            active_keys.add(signal.deduplication_key)
            self._repository.open_or_update(
                monitored_database_id=monitored_database_id,
                sample_id=sample_id,
                threshold_rule_id=signal.threshold_rule_id,
                deduplication_key=signal.deduplication_key,
                severity=signal.severity.value,
                message=signal.message,
            )
        self._repository.resolve_absent(
            monitored_database_id=monitored_database_id,
            active_keys=active_keys,
            resolved_at=evaluated_at,
        )


class AlertManagementService:
    """Casos de uso visibles para las alertas de un usuario."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._alerts = AlertRepository(session)

    def list_for_owner(self, owner_id: UUID, status_filter: str | None) -> list[Alert]:
        return self._alerts.list_for_owner(owner_id, status_filter)

    def acknowledge(self, alert_id: UUID, owner_id: UUID) -> Alert:
        alert = self._alerts.get_for_owner(alert_id, owner_id)
        if alert is None:
            raise ResourceNotFoundError("No se encontró la alerta solicitada.")
        if alert.status == "resolved":
            raise ResourceConflictError("No se puede reconocer una alerta ya resuelta.")
        if alert.status == "open":
            alert.status = "acknowledged"
            self._session.commit()
            self._session.refresh(alert)
        return alert
