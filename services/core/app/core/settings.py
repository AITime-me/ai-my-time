from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Non-secret runtime settings for the core API.

    Provider credentials are intentionally not introduced in this scaffold.
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
