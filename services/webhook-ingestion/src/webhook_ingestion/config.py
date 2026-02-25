"""Webhook ingestion service configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Webhook ingestion service settings."""

    service_name: str = "webhook-ingestion"
    github_webhook_secret: str = ""
    kafka_bootstrap_servers: str = "localhost:9092"
    database_url: str = "postgresql+asyncpg://pi_user:pi_local_password@localhost:5432/pr_intelligence"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}
