from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

from app.domain.models import DatabaseEngine


class CreateMonitoredDatabaseRequest(BaseModel):
    name: str = Field(max_length=120)
    engine: DatabaseEngine
    connection_uri: SecretStr = Field(
        description="URI de conexión. Se cifra antes de persistirse y jamás se devuelve."
    )
    interval_seconds: int = Field(default=30, ge=10, le=86_400)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("El nombre de la instancia no puede estar vacío.")
        return normalized_value

    @field_validator("connection_uri")
    @classmethod
    def connection_uri_must_not_be_blank(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("La URI de conexión no puede estar vacía.")
        return value


class MonitoredDatabaseResponse(BaseModel):
    id: UUID
    name: str
    engine: str
    interval_seconds: int
    is_enabled: bool
    created_at: datetime


class UpdateMonitoredDatabaseRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    interval_seconds: int | None = Field(default=None, ge=10, le=86_400)
    is_enabled: bool | None = None

    @field_validator("name")
    @classmethod
    def updated_name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("El nombre de la instancia no puede estar vacío.")
        return normalized_value

    @model_validator(mode="after")
    def update_must_contain_a_change(self) -> "UpdateMonitoredDatabaseRequest":
        if all(value is None for value in (self.name, self.interval_seconds, self.is_enabled)):
            raise ValueError("Debes enviar al menos un campo para actualizar.")
        return self
