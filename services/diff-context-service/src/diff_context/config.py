"""Diff context service configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Diff context service settings."""

    service_name: str = "diff-context-service"
    github_app_id: str = ""
    github_private_key_path: str = "./secrets/github-app.pem"
    kafka_bootstrap_servers: str = "localhost:9092"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+asyncpg://pi_user:pi_local_password@localhost:5432/pr_intelligence"
    log_level: str = "INFO"

    # Context settings
    context_lines: int = 20  # Lines of surrounding context above/below changes
    max_diff_size_bytes: int = 500_000
    max_files_per_analysis: int = 30

    model_config = {"env_file": ".env", "extra": "ignore"}
