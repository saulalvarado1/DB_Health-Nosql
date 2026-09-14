from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.api.presenters import monitoring_history_response


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

    response = monitoring_history_response(sample)

    assert response.health_score == 80
    assert response.health_status == "warning"
    assert [metric.code for metric in response.metrics] == [
        "connected_clients",
        "used_memory_bytes",
    ]
    assert "connection_uri" not in response.model_dump()
