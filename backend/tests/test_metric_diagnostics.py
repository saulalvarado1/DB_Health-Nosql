from app.domain.models import MetricDiagnosticBasis, MetricDiagnosticStatus
from app.services.health_score import HealthRule
from app.services.metric_diagnostics import diagnose_metric


def test_configured_threshold_drives_status_and_explanation() -> None:
    rule = HealthRule(
        metric_code="memory_usage_percent",
        display_name="Uso de memoria",
        direction="above",
        warning_value=80,
        critical_value=90,
    )

    diagnostic = diagnose_metric(
        metric_code="memory_usage_percent",
        value=92,
        rule=rule,
        previous_value=85,
    )

    assert diagnostic.status is MetricDiagnosticStatus.CRITICAL
    assert diagnostic.basis is MetricDiagnosticBasis.THRESHOLD
    assert "umbral crítico configurado (90)" in diagnostic.message
    assert "expulsar claves" in diagnostic.message


def test_connection_capacity_uses_a_transparent_heuristic() -> None:
    diagnostic = diagnose_metric(
        metric_code="connections_usage_percent",
        value=82,
        rule=None,
        previous_value=78,
    )

    assert diagnostic.status is MetricDiagnosticStatus.WARNING
    assert diagnostic.basis is MetricDiagnosticBasis.HEURISTIC
    assert "80%" in diagnostic.message


def test_cumulative_incident_is_compared_with_the_previous_sample() -> None:
    diagnostic = diagnose_metric(
        metric_code="evicted_keys",
        value=5,
        rule=None,
        previous_value=2,
    )

    assert diagnostic.status is MetricDiagnosticStatus.WARNING
    assert "3 claves expulsadas" in diagnostic.message


def test_uptime_drop_reports_a_restart() -> None:
    diagnostic = diagnose_metric(
        metric_code="uptime_seconds",
        value=30,
        rule=None,
        previous_value=3_600,
    )

    assert diagnostic.status is MetricDiagnosticStatus.WARNING
    assert "se reinició" in diagnostic.message


def test_metric_without_a_universal_limit_is_informational() -> None:
    diagnostic = diagnose_metric(
        metric_code="operations_per_second",
        value=1_000,
        rule=None,
        previous_value=500,
    )

    assert diagnostic.status is MetricDiagnosticStatus.INFORMATIONAL
    assert diagnostic.basis is MetricDiagnosticBasis.INFORMATIONAL
    assert "carga esperada" in diagnostic.message


def test_mongodb_lock_queue_reports_operational_pressure() -> None:
    diagnostic = diagnose_metric(
        metric_code="global_lock_queue_total",
        value=2,
        rule=None,
        previous_value=0,
    )

    assert diagnostic.status is MetricDiagnosticStatus.WARNING
    assert "esperando un bloqueo" in diagnostic.message


def test_redis_persistence_failure_is_critical() -> None:
    diagnostic = diagnose_metric(
        metric_code="persistence_last_save_success",
        value=0,
        rule=None,
        previous_value=1,
    )

    assert diagnostic.status is MetricDiagnosticStatus.CRITICAL
    assert "guardado RDB falló" in diagnostic.message


def test_redis_loading_state_is_explained() -> None:
    diagnostic = diagnose_metric(
        metric_code="loading",
        value=1,
        rule=None,
        previous_value=0,
    )

    assert diagnostic.status is MetricDiagnosticStatus.WARNING
    assert "cargando datos" in diagnostic.message
