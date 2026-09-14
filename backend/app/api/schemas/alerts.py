from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

AlertSeverity = Literal["warning", "critical"]
AlertStatus = Literal["open", "acknowledged", "resolved"]


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    monitored_database_id: UUID
    sample_id: UUID | None
    threshold_rule_id: UUID | None
    severity: AlertSeverity
    status: AlertStatus
    message: str
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
