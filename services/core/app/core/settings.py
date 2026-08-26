from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Non-secret runtime settings for the core API.

    Database and provider credentials are intentionally not introduced in the
    first scaffold. They are added only together with their isolated runtime
    and secret-delivery path.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "A.I. My Time Core"
    app_env: str = "development"
    app_version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
