"""Shared dependencies for webhook ingestion service."""
from __future__ import annotations

from common.kafka.producer import KafkaProducerWrapper

# Shared Kafka producer — initialized during lifespan
kafka_producer: KafkaProducerWrapper | None = None


def get_kafka_producer() -> KafkaProducerWrapper:
    """Get the shared Kafka producer instance."""
    if kafka_producer is None:
        raise RuntimeError("Kafka producer not initialized")
    return kafka_producer
