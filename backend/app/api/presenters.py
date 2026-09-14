from app.api.schemas.monitored_databases import MonitoredDatabaseResponse
from app.api.schemas.monitoring import (
    MetricValueHistoryResponse,
    MonitoringHistoryResponse,
)
from app.domain.models import HealthStatus
from app.infrastructure.persistence.models import MetricSample, MonitoredDatabase


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


def monitoring_history_response(sample: MetricSample) -> MonitoringHistoryResponse:
    """Presenta evidencia histórica normalizada y excluye secretos de conexión."""
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
            )
            for value in sorted(sample.values, key=lambda item: item.metric_definition.code)
        ],
    )
