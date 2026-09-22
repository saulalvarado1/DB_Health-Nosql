from app.api.schemas.monitored_databases import MonitoredDatabaseResponse
from app.api.schemas.monitoring import (
    MetricValueHistoryResponse,
    MonitoringHistoryResponse,
)
from app.api.schemas.thresholds import ThresholdProfileResponse, ThresholdRuleResponse
from app.domain.models import HealthStatus
from app.infrastructure.persistence.models import MonitoredDatabase, ThresholdProfile
from app.services.history import MonitoringHistoryEntry


def monitored_database_response(database: MonitoredDatabase) -> MonitoredDatabaseResponse:
    """Transforma una entidad en respuesta pública y excluye la URI cifrada."""
    if database.schedule is None:
        raise RuntimeError("La instancia monitoreada no tiene programación configurada.")
    return MonitoredDatabaseResponse(
        id=database.id,
        name=database.name,
        engine=database.engine_id,
        interval_seconds=database.schedule.interval_seconds,
        is_enabled=database.is_enabled,
        created_at=database.created_at,
    )


def monitoring_history_response(entry: MonitoringHistoryEntry) -> MonitoringHistoryResponse:
    """Presenta evidencia histórica normalizada y excluye secretos de conexión."""
    sample = entry.sample
    assessment = sample.health_assessment
    if assessment is None:
        raise RuntimeError("La muestra no tiene una evaluación de salud asociada.")
    return MonitoringHistoryResponse(
        sample_id=sample.id,
        collected_at=sample.collected_at,
        collection_succeeded=sample.collection_succeeded,
        error_message=sample.error_message,
        health_score=assessment.score,
        health_status=HealthStatus(assessment.status),
        evaluated_at=assessment.evaluated_at,
        metrics=[
            MetricValueHistoryResponse(
                code=value.metric_definition.code,
                display_name=value.metric_definition.display_name,
                unit=value.metric_definition.unit,
                value=float(value.numeric_value),
                status=entry.diagnostics[value.metric_definition.code].status,
                diagnostic_basis=entry.diagnostics[value.metric_definition.code].basis,
                message=entry.diagnostics[value.metric_definition.code].message,
            )
            for value in sorted(sample.values, key=lambda item: item.metric_definition.code)
        ],
    )


def threshold_profile_response(profile: ThresholdProfile) -> ThresholdProfileResponse:
    """Presenta reglas configurables sin revelar datos de conexión de la instancia."""
    return ThresholdProfileResponse(
        id=profile.id,
        name=profile.name,
        engine=profile.engine_id,
        is_default=profile.is_default,
        rules=[
            ThresholdRuleResponse(
                metric_definition_id=rule.metric_definition.id,
                metric_code=rule.metric_definition.code,
                display_name=rule.metric_definition.display_name,
                unit=rule.metric_definition.unit,
                alert_direction=rule.metric_definition.alert_direction,
                warning_value=float(rule.warning_value),
                critical_value=float(rule.critical_value),
            )
            for rule in sorted(profile.rules, key=lambda item: item.metric_definition.code)
        ],
    )
