from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.domain.models import HealthStatus, MetricDiagnosticBasis, MetricDiagnosticStatus
from app.services.history import MonitoringHistoryEntry
from app.services.metric_diagnostics import MetricDiagnostic
from app.services.reports import ReportExportService


def test_report_export_service_generates_valid_csv() -> None:
    database = SimpleNamespace(
        id=uuid4(),
        name="Production Redis Cluster",
        engine_id="redis",
        interval_seconds=30,
        is_enabled=True,
        created_at=datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
    )
    sample = SimpleNamespace(
        id=uuid4(),
        collected_at=datetime(2026, 9, 24, 10, 0, tzinfo=UTC),
        collection_succeeded=True,
        error_message=None,
        health_assessment=SimpleNamespace(
            score=95,
            status=HealthStatus.HEALTHY,
        ),
        values=[
            SimpleNamespace(
                numeric_value=1.0,
                metric_definition=SimpleNamespace(
                    code="availability",
                    display_name="Disponibilidad",
                    unit="ratio",
                ),
            ),
            SimpleNamespace(
                numeric_value=45.2,
                metric_definition=SimpleNamespace(
                    code="memory_usage_percent",
                    display_name="Uso de memoria",
                    unit="percent",
                ),
            ),
        ],
    )
    entries = [
        MonitoringHistoryEntry(
            sample=sample,
            diagnostics={
                "availability": MetricDiagnostic(
                    status=MetricDiagnosticStatus.HEALTHY,
                    basis=MetricDiagnosticBasis.HEURISTIC,
                    message="Disponible",
                ),
                "memory_usage_percent": MetricDiagnostic(
                    status=MetricDiagnosticStatus.HEALTHY,
                    basis=MetricDiagnosticBasis.HEURISTIC,
                    message="Memoria adecuada",
                ),
            },
        )
    ]

    service = ReportExportService(database, entries)
    csv_text = service.export_csv()

    assert "# Instancia,Production Redis Cluster" in csv_text
    assert "# Motor NoSQL,REDIS" in csv_text
    assert "Fecha_Recoleccion_UTC,Puntuacion_Salud,Estado_Salud,Recoleccion_Exitosa,Error" in csv_text
    assert "2026-09-24 10:00:00,95,healthy,SI" in csv_text
    assert "45.20" in csv_text


def test_report_export_service_generates_valid_json() -> None:
    database = SimpleNamespace(
        id=uuid4(),
        name="Main MongoDB",
        engine_id="mongodb",
        interval_seconds=60,
        is_enabled=True,
        created_at=datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
    )
    sample = SimpleNamespace(
        id=uuid4(),
        collected_at=datetime(2026, 9, 24, 11, 0, tzinfo=UTC),
        collection_succeeded=True,
        error_message=None,
        health_assessment=SimpleNamespace(
            score=100,
            status=HealthStatus.HEALTHY,
        ),
        values=[
            SimpleNamespace(
                numeric_value=1.0,
                metric_definition=SimpleNamespace(
                    code="availability",
                    display_name="Disponibilidad",
                    unit="ratio",
                ),
            ),
        ],
    )
    entries = [
        MonitoringHistoryEntry(
            sample=sample,
            diagnostics={
                "availability": MetricDiagnostic(
                    status=MetricDiagnosticStatus.HEALTHY,
                    basis=MetricDiagnosticBasis.HEURISTIC,
                    message="OK",
                )
            },
        )
    ]

    service = ReportExportService(database, entries)
    json_data = service.export_json()

    assert json_data["database"]["name"] == "Main MongoDB"
    assert json_data["database"]["engine"] == "mongodb"
    assert json_data["summary"]["total_samples"] == 1
    assert json_data["summary"]["latest_health_score"] == 100
    assert json_data["summary"]["latest_health_status"] == "healthy"
    assert len(json_data["samples"]) == 1
    assert json_data["samples"][0]["metrics"][0]["code"] == "availability"
    assert json_data["samples"][0]["metrics"][0]["value"] == 1.0


def test_report_export_empty_samples_handled_gracefully() -> None:
    database = SimpleNamespace(
        id=uuid4(),
        name="Empty DB",
        engine_id="redis",
        interval_seconds=30,
        is_enabled=True,
        created_at=datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
    )
    service = ReportExportService(database, [])
    csv_text = service.export_csv()
    json_data = service.export_json()

    assert "No se registran muestras historicas" in csv_text
    assert json_data["summary"]["total_samples"] == 0
    assert json_data["summary"]["latest_health_score"] is None
