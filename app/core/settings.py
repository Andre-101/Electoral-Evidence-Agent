from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "electoral-evidence-agent"
    app_env: str = "development"
    app_debug: bool = True

    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/electoral_evidence"

    llm_provider: str = "openai"
    llm_api_key: str = "replace_me"
    llm_model: str = "replace_me"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"
    llm_enabled: str = "auto"
    llm_max_tokens: int = 1800

    max_upload_size_mb: int = 200
    upload_dir: str = "data/raw"
    pipeline_version: str = "0.1.0"
    rules_version: str = "0.1.0"
    scoring_version: str = "0.1.0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML config format: {config_path}")
    return data
