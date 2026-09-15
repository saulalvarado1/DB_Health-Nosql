import math

import pytest
from pydantic import ValidationError

from app.api.schemas.thresholds import UpdateThresholdRuleRequest


def test_threshold_update_requires_finite_numeric_values() -> None:
    request = UpdateThresholdRuleRequest(warning_value=80, critical_value=90)

    assert request.warning_value == 80
    assert request.critical_value == 90

    with pytest.raises(ValidationError):
        UpdateThresholdRuleRequest(warning_value=math.inf, critical_value=90)
