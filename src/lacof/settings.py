"""Lacof app settings schema."""

from typing import Literal

from pydantic import HttpUrl, PostgresDsn, SecretStr
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
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: SecretStr = SecretStr("minioadmin")
    S3_ENDPOINT_URL: HttpUrl = HttpUrl("http://localhost:9000")
    S3_BUCKET_NAME: str = "lacof"


lacof_settings = LacofSettings()
