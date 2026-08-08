"""Application configuration.

Settings come from environment variables (or a local ``.env`` file). This module
is infrastructure only — it must not import domain modules.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    development = "development"
    test = "test"
    production = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = Environment.development
    log_level: str = "INFO"

    # Database — SQLAlchemy async URL using the psycopg 3 driver.
    database_url: str = "postgresql+psycopg://forecastly:forecastly@localhost:5432/forecastly"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # CORS — explicit origins only; never "*" for credentialed requests.
    cors_origins: list[str] = Field(default_factory=list)

    # Maximum accepted sales-CSV upload size in bytes (default 5 MB).
    max_upload_bytes: int = 5 * 1024 * 1024

    # Clerk (external auth provider). Optional until wired.
    clerk_secret_key: str | None = None
    clerk_publishable_key: str | None = None

    # Development-only authentication fallback. Ignored in production.
    dev_auth_enabled: bool = True
    dev_auth_subject: str = "dev-user"
    dev_auth_email: str = "dev@forecastly.local"

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.production

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        # Accept a comma-separated string in addition to a JSON array.
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
