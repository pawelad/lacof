"""Lacof app settings schema."""

from typing import Literal

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class LacofSettings(BaseSettings):
    """Lacof app settings."""

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    ENVIRONMENT: Literal["local", "production"] = "local"
    DEBUG: bool = False
    DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://postgres@localhost/lacof"
    )


lacof_settings = LacofSettings()
