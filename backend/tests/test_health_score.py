from app.domain.models import HealthStatus
from app.services.health_score import HealthRule, assess_connection, assess_metrics


def test_available_connection_is_healthy() -> None:
    assessment = assess_connection(is_available=True)

    assert assessment.score == 100
    assert assessment.status is HealthStatus.HEALTHY


def test_unavailable_connection_is_critical() -> None:
    assessment = assess_connection(is_available=False)

    assert assessment.score == 0
    assert assessment.status is HealthStatus.CRITICAL


def test_metric_above_critical_threshold_is_critical() -> None:
    assessment = assess_metrics(
        {"memory_usage_percent": 92},
        [
            HealthRule(
                metric_code="memory_usage_percent",
                display_name="Uso de memoria",
                direction="above",
                warning_value=80,
                critical_value=90,
            )
        ],
    )

    assert assessment.status is HealthStatus.CRITICAL
    assert assessment.score == 50


def test_metric_below_critical_threshold_is_critical() -> None:
    assessment = assess_metrics(
        {"availability": 0},
        [
            HealthRule(
                metric_code="availability",
                display_name="Disponibilidad",
                direction="below",
                warning_value=0.5,
                critical_value=0,
            )
        ],
    )

    assert assessment.status is HealthStatus.CRITICAL
