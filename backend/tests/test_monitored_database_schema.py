import pytest
from pydantic import ValidationError

from app.api.schemas.monitored_databases import (
    CreateMonitoredDatabaseRequest,
    UpdateMonitoredDatabaseRequest,
)
from app.domain.models import DatabaseEngine


def test_name_is_normalized_before_registering_a_database() -> None:
    request = CreateMonitoredDatabaseRequest(
        name="  Redis principal  ",
        engine=DatabaseEngine.REDIS,
        connection_uri="redis://localhost:6379/0",
    )

    assert request.name == "Redis principal"


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_database_name_is_rejected(name: str) -> None:
    with pytest.raises(ValidationError, match="nombre de la instancia"):
        CreateMonitoredDatabaseRequest(
            name=name,
            engine=DatabaseEngine.REDIS,
            connection_uri="redis://localhost:6379/0",
        )


def test_blank_connection_uri_is_rejected() -> None:
    with pytest.raises(ValidationError, match="URI de conexión"):
        CreateMonitoredDatabaseRequest(
            name="Redis principal",
            engine=DatabaseEngine.REDIS,
            connection_uri="   ",
        )


def test_update_request_requires_a_change_and_normalizes_name() -> None:
    with pytest.raises(ValidationError, match="al menos un campo"):
        UpdateMonitoredDatabaseRequest()

    request = UpdateMonitoredDatabaseRequest(name="  Redis secundario  ")

    assert request.name == "Redis secundario"
