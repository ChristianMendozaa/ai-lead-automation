"""Environment-driven settings. One place to read env vars from."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://leads:leads@postgres:5432/leads"
    app_encryption_key: str
    setup_token: str
    openai_model: str = "gpt-4o-mini"
    duplicate_window_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
