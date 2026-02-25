"""Notification service configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Notification service settings."""

    service_name: str = "notification-service"
    github_app_id: str = ""
    github_private_key_path: str = "./secrets/github-app.pem"
    kafka_bootstrap_servers: str = "localhost:9092"
    database_url: str = "postgresql+asyncpg://pi_user:pi_local_password@localhost:5432/pr_intelligence"
    log_level: str = "INFO"
    confidence_threshold: float = 0.6

    model_config = {"env_file": ".env", "extra": "ignore"}
