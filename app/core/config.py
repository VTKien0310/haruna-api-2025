import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_file() -> str | None:
    if os.environ.get("ENVIRONMENT") == "testing":
        return None
    return ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: str = "development"

    APP_NAME: str = "Haruna API 2025"
    APP_VERSION: str = "2025"
    APP_PORT: int = 8000
    APP_ENABLE_DOCS: bool = False
    LOG_LEVEL: str = "INFO"
    SLOW_REQUEST_THRESHOLD_MS: int = 5000

    API_PREFIX: str = "/api"
    API_ALLOW_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    DB_HOST: str = ""
    DB_PORT: int = 5432
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = ""
    DB_SCHEMA: str = "public"
    DB_POOL_RECYCLE_SECONDS: int = 300
    DB_COMMAND_TIMEOUT_SECONDS: int = 10
    DB_CONNECT_TIMEOUT_SECONDS: int = 10

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    AI_API_ENDPOINT: str = ""
    AI_API_KEY: str = ""
    AI_TRANSLATION_MODEL: str = "gpt-5.6-luna"


settings = Settings()
