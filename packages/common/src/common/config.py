"""Shared configuration management using pydantic-settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class CommonSettings(BaseSettings):
    """Base settings shared across all services.

    Values are read from environment variables. Services extend this
    class with their own specific settings.
    """

    kafka_bootstrap_servers: str = "localhost:9092"
    database_url: str = "postgresql+asyncpg://pi_user:pi_local_password@localhost:5432/pr_intelligence"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"

    # Application-wide settings
    confidence_threshold: float = 0.6
    max_diff_size_bytes: int = 500_000
    max_files_per_analysis: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}
