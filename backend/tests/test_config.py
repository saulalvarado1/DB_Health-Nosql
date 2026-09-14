import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(
    "variable_name, field_name",
    [
        ("DATABASE_URL", "database_url"),
        ("JWT_SECRET_KEY", "jwt_secret_key"),
        ("CREDENTIALS_ENCRYPTION_KEY", "credentials_encryption_key"),
    ],
)
def test_required_security_configuration_cannot_fall_back_to_code(
    monkeypatch: pytest.MonkeyPatch, variable_name: str, field_name: str
) -> None:
    monkeypatch.delenv(variable_name)

    with pytest.raises(ValidationError, match=field_name):
        Settings(_env_file=None)


def test_settings_accept_values_from_environment() -> None:
    settings = Settings(_env_file=None)

    assert settings.database_url.hosts()[0]["host"] == "localhost"
    assert settings.jwt_secret_key.get_secret_value() == "test-jwt-secret-not-for-production"


def test_worker_settings_have_bounded_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.monitoring_worker_poll_seconds == 5
    assert settings.monitoring_lease_seconds == 90
    assert settings.monitoring_worker_batch_size == 25
