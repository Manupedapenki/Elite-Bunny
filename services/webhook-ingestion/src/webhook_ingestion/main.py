"""FastAPI application entry point for webhook ingestion service."""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from common.kafka.producer import KafkaProducerWrapper
from common.logging import setup_logging

from . import dependencies
from .config import Settings
from .routes import health, webhooks

settings = Settings()
setup_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle — start/stop Kafka producer."""
    logger.info("service.starting", service=settings.service_name)

    dependencies.kafka_producer = KafkaProducerWrapper(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=settings.service_name,
    )
    await dependencies.kafka_producer.start()

    yield

    await dependencies.kafka_producer.stop()
    logger.info("service.stopped", service=settings.service_name)


app = FastAPI(
    title="Webhook Ingestion Service",
    description="Receives GitHub webhook events and publishes to Kafka",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(webhooks.router)
