from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Non-secret runtime settings for the core API.

    The non-production provider is opt-in and fails closed. Credentials stay in
    a protected file path, never in the repository or application logs.
    DATABASE_URL is optional locally and required by the migration/deploy
    commands; it is never logged by application code.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "A.I. My Time Core"
    app_env: str = "development"
    app_version: str = "0.1.0"
    database_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_lead_webhook_secret: str | None = None
    diagnostic_provider: Literal["disabled", "yandex_nonprod"] = "disabled"
    diagnostic_prompt_version: str = "v1"
    yandex_nonprod_folder_id: str | None = None
    yandex_nonprod_api_key_path: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
