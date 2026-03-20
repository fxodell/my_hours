import warnings
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

_INSECURE_DEFAULT_KEY = "dev-only-insecure-key-set-SECRET_KEY-in-env"


class Settings(BaseSettings):
    # App
    app_name: str = "MyHours"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/myhours"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/myhours"

    # Auth — set SECRET_KEY in .env (generate with: openssl rand -hex 32)
    secret_key: str = _INSECURE_DEFAULT_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "https://myhours.nfmconsulting.com"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.secret_key == _INSECURE_DEFAULT_KEY and not s.debug:
        raise RuntimeError(
            "SECRET_KEY is not set. Generate one with: openssl rand -hex 32"
        )
    if s.secret_key == _INSECURE_DEFAULT_KEY:
        warnings.warn("Using insecure default SECRET_KEY — set SECRET_KEY in .env for production")
    return s


settings = get_settings()
