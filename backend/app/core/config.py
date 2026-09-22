from functools import lru_cache

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores de configuración obtenidos del entorno."""

    app_name: str = "DB Health Monitor"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    database_url: PostgresDsn
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    credentials_encryption_key: SecretStr
    log_level: str = "INFO"
    cors_allowed_origins: list[str] = Field(default_factory=list)
    monitoring_worker_poll_seconds: int = Field(default=5, ge=1, le=300)
    monitoring_lease_seconds: int = Field(default=90, ge=10, le=3_600)
    monitoring_worker_batch_size: int = Field(default=25, ge=1, le=500)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
