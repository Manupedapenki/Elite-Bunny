"""FastAPI app entry point for diff context service."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI

from common.kafka.consumer import KafkaConsumerWrapper
from common.kafka.producer import KafkaProducerWrapper
from common.logging import setup_logging

from .config import Settings
from .consumer import handle_pr_event

settings = Settings()
setup_logging(settings.service_name, settings.log_level)
logger = structlog.get_logger()

# Shared resources
kafka_producer: KafkaProducerWrapper | None = None
redis_client: aioredis.Redis | None = None


def get_kafka_producer() -> KafkaProducerWrapper:
    """Get the shared Kafka producer."""
    if kafka_producer is None:
        raise RuntimeError("Kafka producer not initialized")
    return kafka_producer


def get_redis_client() -> aioredis.Redis | None:
    """Get the shared Redis client."""
    return redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle."""
    global kafka_producer, redis_client

    logger.info("service.starting", service=settings.service_name)

    # Initialize Redis
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)

    # Initialize Kafka producer
    kafka_producer = KafkaProducerWrapper(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        client_id=f"{settings.service_name}-producer",
    )
    await kafka_producer.start()

    # Initialize Kafka consumer
    consumer = KafkaConsumerWrapper(
        topic="pr.events",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="diff-context-service",
        client_id=f"{settings.service_name}-consumer",
    )
    await consumer.start()

    # Start consuming in background
    consumer_task = asyncio.create_task(consumer.consume(handle_pr_event))

    yield

    # Shutdown
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await consumer.stop()
    await kafka_producer.stop()
    if redis_client:
        await redis_client.aclose()
    logger.info("service.stopped", service=settings.service_name)


app = FastAPI(
    title="Diff Context Service",
    description="Fetches PR diffs and enriches with surrounding code context",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "healthy", "service": "diff-context-service"}
