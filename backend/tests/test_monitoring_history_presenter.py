from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.api.presenters import monitoring_history_response
from app.domain.models import MetricDiagnosticBasis, MetricDiagnosticStatus
from app.services.history import MonitoringHistoryEntry
from app.services.metric_diagnostics import MetricDiagnostic


def test_history_presenter_returns_normalized_metric_values_without_connection_data() -> None:
    sample = SimpleNamespace(
        id=uuid4(),
        collected_at=datetime(2026, 9, 14, 14, 0, tzinfo=UTC),
        collection_succeeded=True,
        error_message=None,
        health_assessment=SimpleNamespace(
            score=80,
            status="warning",
            evaluated_at=datetime(2026, 9, 14, 14, 0, tzinfo=UTC),
        ),
        values=[
            SimpleNamespace(
                numeric_value=12.5,
                metric_definition=SimpleNamespace(
                    code="used_memory_bytes",
                    display_name="Memoria usada",
                    unit="bytes",
                ),
            ),
            SimpleNamespace(
                numeric_value=4,
                metric_definition=SimpleNamespace(
                    code="connected_clients",
                    display_name="Clientes conectados",
                    unit="clients",
                ),
            ),
        ],
    )

    response = monitoring_history_response(
        MonitoringHistoryEntry(
            sample=sample,
            diagnostics={
                "used_memory_bytes": MetricDiagnostic(
                    status=MetricDiagnosticStatus.INFORMATIONAL,
                    basis=MetricDiagnosticBasis.INFORMATIONAL,
                    message="La memoria absoluta necesita contexto.",
                ),
                "connected_clients": MetricDiagnostic(
                    status=MetricDiagnosticStatus.HEALTHY,
                    basis=MetricDiagnosticBasis.HEURISTIC,
                    message="No se detectó presión de conexiones.",
                ),
            },
        )
    )

    assert response.health_score == 80
    assert response.health_status == "warning"
    assert [metric.code for metric in response.metrics] == [
        "connected_clients",
        "used_memory_bytes",
    ]
    assert response.metrics[0].status == "healthy"
    assert response.metrics[0].diagnostic_basis == "heuristic"
    assert response.metrics[0].message == "No se detectó presión de conexiones."
    assert "connection_uri" not in response.model_dump()
