from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    APP_NAME: str = "Haruna API 2025"
    APP_VERSION: str = "2025"
    APP_PORT: int = 8000
    APP_ENABLE_DOCS: bool = False

    API_PREFIX: str = "/api"
    API_ALLOW_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""


settings = Settings()
