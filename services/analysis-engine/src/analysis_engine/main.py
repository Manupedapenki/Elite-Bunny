"""FastAPI app entry point for analysis engine service."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from common.kafka.consumer import KafkaConsumerWrapper
from common.kafka.producer import KafkaProducerWrapper
from common.logging import setup_logging

from .config import Settings
from .consumer import handle_analysis_request

settings = Settings()
setup_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger()

kafka_producer: KafkaProducerWrapper | None = None


def get_kafka_producer() -> KafkaProducerWrapper:
    """Get the shared Kafka producer."""
    if kafka_producer is None:
        raise RuntimeError("Kafka producer not initialized")
    return kafka_producer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle."""
    global kafka_producer

    logger.info("service.starting", service=settings.service_name)

    kafka_producer = KafkaProducerWrapper(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=f"{settings.service_name}-producer",
    )
    await kafka_producer.start()

    consumer = KafkaConsumerWrapper(
        topic="analysis.requests",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="analysis-engine",
        client_id=f"{settings.service_name}-consumer",
    )
    await consumer.start()

    consumer_task = asyncio.create_task(consumer.consume(handle_analysis_request))

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await consumer.stop()
    await kafka_producer.stop()
    logger.info("service.stopped", service=settings.service_name)


app = FastAPI(
    title="Analysis Engine",
    description="Orchestrates LLM analysis of PR diffs",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "healthy", "service": "analysis-engine"}
