from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class DatabaseEngine(StrEnum):
    MONGODB = "mongodb"
    REDIS = "redis"


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MetricDiagnosticStatus(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    INFORMATIONAL = "informational"


class MetricDiagnosticBasis(StrEnum):
    THRESHOLD = "threshold"
    HEURISTIC = "heuristic"
    INFORMATIONAL = "informational"


@dataclass(frozen=True, slots=True)
class MetricSample:
    database_id: UUID
    collected_at: datetime
    values: Mapping[str, float | int | str | bool]


@dataclass(frozen=True, slots=True)
class HealthAssessment:
    score: int
    status: HealthStatus
    reasons: tuple[str, ...]
