from collections.abc import Mapping
from dataclasses import dataclass

from app.domain.models import HealthAssessment, HealthStatus


@dataclass(frozen=True, slots=True)
class HealthRule:
    metric_code: str
    display_name: str
    direction: str
    warning_value: float
    critical_value: float


def assess_connection(is_available: bool) -> HealthAssessment:
    """Fallback de disponibilidad cuando una conexión no puede recolectarse."""
    if is_available:
        return HealthAssessment(100, HealthStatus.HEALTHY, ())
    return HealthAssessment(0, HealthStatus.CRITICAL, ("La base de datos no responde.",))


def assess_metrics(
    metrics: Mapping[str, float], rules: list[HealthRule]
) -> HealthAssessment:
    """Evalúa valores atómicos con reglas configurables y penalizaciones acumuladas."""
    score = 100
    has_warning = False
    has_critical = False
    reasons: list[str] = []

    for rule in rules:
        value = metrics.get(rule.metric_code)
        if value is None:
            continue
        severity = _severity(value, rule)
        if severity is HealthStatus.CRITICAL:
            has_critical = True
            score -= 50
            reasons.append(f"{rule.display_name} alcanzó un nivel crítico.")
        elif severity is HealthStatus.WARNING:
            has_warning = True
            score -= 20
            reasons.append(f"{rule.display_name} alcanzó un nivel de advertencia.")

    if has_critical:
        status = HealthStatus.CRITICAL
    elif has_warning:
        status = HealthStatus.WARNING
    else:
        status = HealthStatus.HEALTHY
    return HealthAssessment(max(0, score), status, tuple(reasons))


def _severity(value: float, rule: HealthRule) -> HealthStatus | None:
    if rule.direction == "above":
        if value >= rule.critical_value:
            return HealthStatus.CRITICAL
        if value >= rule.warning_value:
            return HealthStatus.WARNING
    elif rule.direction == "below":
        if value <= rule.critical_value:
            return HealthStatus.CRITICAL
        if value <= rule.warning_value:
            return HealthStatus.WARNING
    return None
