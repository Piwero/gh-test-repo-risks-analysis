from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    secret_key: SecretStr
    database_url: str = "sqlite:///./data/app.db"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    upload_dir: Path = Path("./data/uploads")
    max_upload_bytes: int = 5 * 1024 * 1024
    allowed_upload_types: list[str] = ["application/pdf", "image/png", "image/jpeg"]

    webhook_timeout_seconds: float = 5.0

    frontend_url: str = "http://localhost:3000"

    cors_origins: list[str] = []
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
