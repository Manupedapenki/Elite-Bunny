"""FastAPI app entry point for LLM service."""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from common.logging import setup_logging

from .config import Settings
from .routes import completions

settings = Settings()
setup_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle."""
    logger.info("service.starting", service=settings.service_name)
    yield
    logger.info("service.stopped", service=settings.service_name)


app = FastAPI(
    title="LLM Service",
    description="Claude API wrapper with prompt management for PR analysis",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(completions.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "healthy", "service": "llm-service"}
