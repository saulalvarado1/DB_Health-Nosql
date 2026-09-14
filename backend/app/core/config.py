from functools import lru_cache

from pydantic import PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores de configuración obtenidos del entorno."""

    app_name: str = "DB Health Monitor"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    database_url: PostgresDsn = PostgresDsn(
        "postgresql+psycopg://dbhealth:dbhealth@localhost:5432/db_health_monitor"
    )
    jwt_secret_key: SecretStr = SecretStr("change-this-before-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    credentials_encryption_key: SecretStr | None = None
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @model_validator(mode="after")
    def production_secrets_must_be_configured(self) -> "Settings":
        if self.environment.lower() != "production":
            return self
        if self.jwt_secret_key.get_secret_value() == "change-this-before-production":
            raise ValueError("JWT_SECRET_KEY debe definirse en producción.")
        if self.credentials_encryption_key is None:
            raise ValueError("CREDENTIALS_ENCRYPTION_KEY debe definirse en producción.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
