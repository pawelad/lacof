"""Lacof app settings schema."""

from typing import Literal

from pydantic import HttpUrl, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LacofSettings(BaseSettings):
    """Lacof app settings.

    Attributes:
        ENVIRONMENT: App environment. Can be one of 'local', 'production' or 'test'.
        DEBUG: Whether the app is running in debug mode.
        DATABASE_URL: Database URL.
        TEST_DATABASE_URL: Test database URL.
        REDIS_URL: Redis URL.
        AWS_ACCESS_KEY_ID: AWS access key ID.
        AWS_SECRET_ACCESS_KEY: AWS secret access key.
        S3_ENDPOINT_URL: S3 endpoint URL. Needed for using MinIO instead of S3.
        S3_BUCKET_NAME: S3 bucket name
        CLIP_MODEL_NAME: Clip ML model name.
        SENTRY_DSN: Sentry DSN for its integration. Disabled by default.
    """

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    ENVIRONMENT: Literal["production", "local", "test"] = "local"
    DEBUG: bool = False

    DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://postgres@localhost/lacof"
    )
    TEST_DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://postgres@localhost/lacof-test"
    )
    REDIS_URL: RedisDsn = RedisDsn("redis://localhost:6379/0")

    # S3
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: SecretStr = SecretStr("minioadmin")
    S3_ENDPOINT_URL: HttpUrl = HttpUrl("http://localhost:9000")
    S3_BUCKET_NAME: str = "lacof"

    # ML
    CLIP_MODEL_NAME: str = "clip-ViT-B-32"

    # Misc
    SENTRY_DSN: HttpUrl | None = None


lacof_settings = LacofSettings()
