from typing import Literal
from uuid import UUID

from pydantic import BaseModel, FiniteFloat

AlertDirection = Literal["above", "below"]


class ThresholdRuleResponse(BaseModel):
    metric_definition_id: UUID
    metric_code: str
    display_name: str
    unit: str
    alert_direction: AlertDirection
    warning_value: float
    critical_value: float


class ThresholdProfileResponse(BaseModel):
    id: UUID
    name: str
    engine: str
    is_default: bool
    rules: list[ThresholdRuleResponse]


class UpdateThresholdRuleRequest(BaseModel):
    warning_value: FiniteFloat
    critical_value: FiniteFloat
