import pytest

from app.domain.errors import ConfigurationError
from app.services.thresholds import validate_threshold_pair


def test_ascending_thresholds_require_warning_before_critical() -> None:
    validate_threshold_pair("above", 80, 90)

    with pytest.raises(ConfigurationError, match="warning debe ser menor"):
        validate_threshold_pair("above", 90, 90)


def test_descending_thresholds_require_warning_before_critical() -> None:
    validate_threshold_pair("below", 0.5, 0)

    with pytest.raises(ConfigurationError, match="warning debe ser mayor"):
        validate_threshold_pair("below", 0, 0.5)
