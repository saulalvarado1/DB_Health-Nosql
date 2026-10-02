from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.secrets import CredentialsCipher
from app.domain.errors import ConfigurationError, ConnectorUnavailableError
from app.domain.models import HealthStatus
from app.infrastructure.connectors.registry import ConnectorRegistry
from app.infrastructure.persistence.models import (
    HealthAssessment,
    MetricDefinition,
    MetricSample,
    MetricValue,
    MonitoredDatabase,
    ThresholdRule,
)
from app.infrastructure.repositories.alerts import AlertRepository
from app.infrastructure.repositories.metrics import MetricCatalogRepository
from app.infrastructure.repositories.thresholds import ThresholdProfileRepository
from app.services.alerts import AlertLifecycleService, AlertSignal
from app.services.health_score import (
    HealthRule,
    assess_connection,
    assess_metrics,
    severity_for_rule,
)
from app.services.notifications import TelegramNotificationService


@dataclass(frozen=True, slots=True)
class MonitoringRunResult:
    sample_id: UUID
    collected_at: datetime
    collection_succeeded: bool
    health_score: int
    health_status: HealthStatus
    metric_count: int


class MonitoringService:
    """Orquesta una recolección sin conocer detalles de MongoDB o Redis."""

    def __init__(
        self,
        session: Session,
        cipher: CredentialsCipher,
        connectors: ConnectorRegistry,
        notifier: TelegramNotificationService | None = None,
    ) -> None:
        self._session = session
        self._cipher = cipher
        self._connectors = connectors
        self._metric_catalog = MetricCatalogRepository(session)
        self._threshold_profiles = ThresholdProfileRepository(session)
        self._alerts_repo = AlertRepository(session)
        self._alerts = AlertLifecycleService(self._alerts_repo)
        self._notifier = notifier or TelegramNotificationService(cipher=cipher)

    def collect_once(self, monitored_database: MonitoredDatabase) -> MonitoringRunResult:
        collected_at = datetime.now(UTC)
        try:
            connection_uri = self._cipher.decrypt(monitored_database.connection_uri_encrypted)
            connector = self._connectors.get(monitored_database.engine_id)
            collected_metrics = connector.collect_metrics(connection_uri)
        except ConnectorUnavailableError:
            return self._store_failed_sample(monitored_database, collected_at)
        except ValueError as error:
            raise ConfigurationError("No se pudo leer la credencial de la instancia.") from error

        sample = MetricSample(
            monitored_database_id=monitored_database.id,
            collected_at=collected_at,
            collection_succeeded=True,
        )
        definitions = self._metric_catalog.enabled_for_engine(monitored_database.engine_id)
        for code, numeric_value in collected_metrics.items():
            definition = definitions.get(code)
            if definition is not None:
                sample.values.append(
                    MetricValue(metric_definition_id=definition.id, numeric_value=numeric_value)
                )

        configured_rules = self._threshold_profiles.rules_for_database(monitored_database.id)
        health_rules = [self._health_rule(rule, definition) for rule, definition in configured_rules]
        assessment = assess_metrics(collected_metrics, health_rules)
        sample.health_assessment = HealthAssessment(
            score=assessment.score,
            status=assessment.status.value,
            evaluated_at=collected_at,
        )
        self._session.add(sample)
        self._session.flush()
        active_alerts_before = {
            alert.deduplication_key: alert.severity
            for alert in self._alerts_repo.list_active_for_database(monitored_database.id)
        }
        signals = self._threshold_alert_signals(collected_metrics, configured_rules)
        self._alerts.synchronize(
            monitored_database_id=monitored_database.id,
            sample_id=sample.id,
            signals=signals,
            evaluated_at=collected_at,
        )
        self._dispatch_notifications(
            monitored_database=monitored_database,
            active_alerts_before=active_alerts_before,
            current_signals=signals,
            health_score=assessment.score,
            health_status=assessment.status.value,
        )
        self._session.commit()
        self._session.refresh(sample)
        return MonitoringRunResult(
            sample_id=sample.id,
            collected_at=sample.collected_at,
            collection_succeeded=True,
            health_score=assessment.score,
            health_status=assessment.status,
            metric_count=len(sample.values),
        )

    def _store_failed_sample(
        self, monitored_database: MonitoredDatabase, collected_at: datetime
    ) -> MonitoringRunResult:
        assessment = assess_connection(is_available=False)
        sample = MetricSample(
            monitored_database_id=monitored_database.id,
            collected_at=collected_at,
            collection_succeeded=False,
            error_message="No fue posible conectar con la instancia monitoreada.",
        )
        sample.health_assessment = HealthAssessment(
            score=assessment.score,
            status=assessment.status.value,
            evaluated_at=collected_at,
        )
        self._session.add(sample)
        self._session.flush()
        active_alerts_before = {
            alert.deduplication_key: alert.severity
            for alert in self._alerts_repo.list_active_for_database(monitored_database.id)
        }
        signals = (
            AlertSignal(
                deduplication_key="connection-unavailable",
                severity=HealthStatus.CRITICAL,
                message="La instancia monitoreada no responde.",
                threshold_rule_id=None,
            ),
        )
        self._alerts.synchronize(
            monitored_database_id=monitored_database.id,
            sample_id=sample.id,
            signals=signals,
            evaluated_at=collected_at,
        )
        self._dispatch_notifications(
            monitored_database=monitored_database,
            active_alerts_before=active_alerts_before,
            current_signals=signals,
            health_score=assessment.score,
            health_status=assessment.status.value,
        )
        self._session.commit()
        self._session.refresh(sample)
        return MonitoringRunResult(
            sample_id=sample.id,
            collected_at=sample.collected_at,
            collection_succeeded=False,
            health_score=assessment.score,
            health_status=assessment.status,
            metric_count=0,
        )

    def _dispatch_notifications(
        self,
        *,
        monitored_database: MonitoredDatabase,
        active_alerts_before: dict[str, str],
        current_signals: tuple[AlertSignal, ...] | list[AlertSignal],
        health_score: int,
        health_status: str,
    ) -> None:
        if (
            not monitored_database.telegram_notifications_enabled
            or not monitored_database.telegram_chat_id
        ):
            return

        current_signals_by_key = {signal.deduplication_key: signal for signal in current_signals}

        for key, signal in current_signals_by_key.items():
            prev_severity = active_alerts_before.get(key)
            if prev_severity is None:
                self._notifier.notify_alert_event(
                    monitored_database,
                    event_type=signal.severity.value,
                    message=signal.message,
                    health_score=health_score,
                    health_status=health_status,
                )
            elif prev_severity == "warning" and signal.severity.value == "critical":
                self._notifier.notify_alert_event(
                    monitored_database,
                    event_type="critical",
                    message=f"Escalamiento a crítico: {signal.message}",
                    health_score=health_score,
                    health_status=health_status,
                )

        if (
            active_alerts_before
            and not current_signals
            and health_status == HealthStatus.HEALTHY.value
        ):
            self._notifier.notify_alert_event(
                monitored_database,
                event_type="recovery",
                message="Todas las alertas activas han sido resueltas. La base de datos opera con normalidad.",
                health_score=health_score,
                health_status=health_status,
            )

    @staticmethod
    def _health_rule(rule: ThresholdRule, definition: MetricDefinition) -> HealthRule:
        return HealthRule(
            metric_code=definition.code,
            display_name=definition.display_name,
            direction=definition.alert_direction,
            warning_value=float(rule.warning_value),
            critical_value=float(rule.critical_value),
        )

    def _threshold_alert_signals(
        self,
        metrics: dict[str, float],
        configured_rules: list[tuple[ThresholdRule, MetricDefinition]],
    ) -> list[AlertSignal]:
        signals: list[AlertSignal] = []
        for rule, definition in configured_rules:
            value = metrics.get(definition.code)
            if value is None:
                continue
            severity = severity_for_rule(value, self._health_rule(rule, definition))
            if severity not in {HealthStatus.WARNING, HealthStatus.CRITICAL}:
                continue
            signals.append(
                AlertSignal(
                    deduplication_key=f"threshold-rule:{rule.id}",
                    severity=severity,
                    message=f"{definition.display_name} alcanzó un nivel {severity.value}.",
                    threshold_rule_id=rule.id,
                )
            )
        return signals
