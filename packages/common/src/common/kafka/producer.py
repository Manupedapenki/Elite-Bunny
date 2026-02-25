"""Async Kafka producer wrapper using aiokafka."""
from __future__ import annotations

import json
from typing import Any, Optional

import structlog
from aiokafka import AIOKafkaProducer

logger = structlog.get_logger()


class KafkaProducerWrapper:
    """Async Kafka producer with JSON serialization and structured logging."""

    def __init__(self, bootstrap_servers: str, client_id: str = "pr-intelligence") -> None:
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        """Start the Kafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._client_id,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retry_backoff_ms=100,
            request_timeout_ms=30000,
        )
        await self._producer.start()
        logger.info("kafka.producer.started", bootstrap_servers=self._bootstrap_servers)

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("kafka.producer.stopped")

    async def send(
        self,
        topic: str,
        value: dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[list[tuple[str, bytes]]] = None,
    ) -> None:
        """Send a message to a Kafka topic.

        Args:
            topic: Target Kafka topic.
            value: Message payload (will be JSON-serialized).
            key: Optional message key for partitioning.
            headers: Optional message headers.
        """
        if not self._producer:
            raise RuntimeError("Producer not started. Call start() first.")

        delivery_id = value.get("delivery_id", "unknown")
        try:
            result = await self._producer.send_and_wait(
                topic=topic,
                value=value,
                key=key,
                headers=headers,
            )
            logger.info(
                "kafka.message.sent",
                topic=topic,
                partition=result.partition,
                offset=result.offset,
                delivery_id=delivery_id,
            )
        except Exception:
            logger.exception(
                "kafka.message.send_failed",
                topic=topic,
                delivery_id=delivery_id,
            )
            raise
