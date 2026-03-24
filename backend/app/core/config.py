import warnings
from urllib.parse import quote_plus
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
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Auth — set SECRET_KEY in .env (generate with: openssl rand -hex 32)
    secret_key: str = _INSECURE_DEFAULT_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173", "https://myhours.nfmconsulting.com"]

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Support environments that only provide POSTGRES_* (common in production/docker).
    if (
        s.database_url == "postgresql+asyncpg://postgres:postgres@localhost:5432/myhours"
        and s.postgres_user
        and s.postgres_password
        and s.postgres_db
    ):
        user = quote_plus(s.postgres_user)
        password = quote_plus(s.postgres_password)
        host = s.postgres_host or "localhost"
        port = s.postgres_port or 5432
        db = s.postgres_db
        s.database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

    if (
        s.database_url_sync == "postgresql+psycopg2://postgres:postgres@localhost:5432/myhours"
        and s.postgres_user
        and s.postgres_password
        and s.postgres_db
    ):
        user = quote_plus(s.postgres_user)
        password = quote_plus(s.postgres_password)
        host = s.postgres_host or "localhost"
        port = s.postgres_port or 5432
        db = s.postgres_db
        s.database_url_sync = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

    if s.secret_key == _INSECURE_DEFAULT_KEY and not s.debug:
        raise RuntimeError(
            "SECRET_KEY is not set. Generate one with: openssl rand -hex 32"
        )
    if s.secret_key == _INSECURE_DEFAULT_KEY:
        warnings.warn("Using insecure default SECRET_KEY — set SECRET_KEY in .env for production")
    return s


settings = get_settings()
