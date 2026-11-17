from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "python-control-layer"
    app_environment: str = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    control_db_url: str = "sqlite:///./runtime/control.db"
    data_root: str = "/data/authoritative"
    manifest_root: str = "/data/manifests"
    staging_root: str = "/data/staging"
    results_root: str = "/data/results"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
