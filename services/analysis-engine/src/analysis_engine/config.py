"""Analysis engine service configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Analysis engine settings."""

    service_name: str = "analysis-engine"
    llm_service_url: str = "http://localhost:8004"
    kafka_bootstrap_servers: str = "localhost:9092"
    database_url: str = "postgresql+asyncpg://pi_user:pi_local_password@localhost:5432/pr_intelligence"
    log_level: str = "INFO"
    confidence_threshold: float = 0.6

    model_config = {"env_file": ".env", "extra": "ignore"}
