"""FastAPI app entry point for notification service."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from common.kafka.consumer import KafkaConsumerWrapper
from common.logging import setup_logging

from .config import Settings
from .consumer import handle_analysis_result

settings = Settings()
setup_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle."""
    logger.info("service.starting", service=settings.service_name)

    consumer = KafkaConsumerWrapper(
        topic="analysis.results",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="notification-service",
        client_id=f"{settings.service_name}-consumer",
    )
    await consumer.start()

    consumer_task = asyncio.create_task(consumer.consume(handle_analysis_result))

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await consumer.stop()
    logger.info("service.stopped", service=settings.service_name)


app = FastAPI(
    title="Notification Service",
    description="Posts review comments and summaries to GitHub PRs",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "healthy", "service": "notification-service"}
