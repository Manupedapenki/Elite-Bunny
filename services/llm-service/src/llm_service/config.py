"""LLM service configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """LLM service settings."""

    service_name: str = "llm-service"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    default_model: str = "gemini-2.0-flash"
    log_level: str = "INFO"

    # Rate limiting
    max_requests_per_minute: int = 50
    request_timeout_seconds: int = 120

    # Prompt paths
    prompts_dir: str = "/app/prompts"

    model_config = {"env_file": ".env", "extra": "ignore"}
