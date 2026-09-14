from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.models import HealthStatus
from app.services.monitoring import MonitoringRunResult


class MonitoringRunResponse(BaseModel):
    sample_id: UUID
    collected_at: datetime
    collection_succeeded: bool
    health_score: int
    health_status: HealthStatus
    metric_count: int

    @classmethod
    def from_result(cls, result: MonitoringRunResult) -> "MonitoringRunResponse":
        return cls(
            sample_id=result.sample_id,
            collected_at=result.collected_at,
            collection_succeeded=result.collection_succeeded,
            health_score=result.health_score,
            health_status=result.health_status,
            metric_count=result.metric_count,
        )
