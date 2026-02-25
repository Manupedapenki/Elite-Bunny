"""Async Kafka consumer wrapper using aiokafka."""
from __future__ import annotations

import json
from typing import Any, Callable, Coroutine, Optional

import structlog
from aiokafka import AIOKafkaConsumer

logger = structlog.get_logger()


class KafkaConsumerWrapper:
    """Async Kafka consumer with JSON deserialization and manual commit."""

    def __init__(
        self,
        topic: str,
        bootstrap_servers: str,
        group_id: str,
        client_id: str = "pr-intelligence",
    ) -> None:
        self._topic = topic
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._client_id = client_id
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False

    async def start(self) -> None:
        """Start the Kafka consumer."""
        self._consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            client_id=self._client_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            max_poll_interval_ms=300000,  # 5 minutes for long LLM calls
        )
        await self._consumer.start()
        self._running = True
        logger.info(
            "kafka.consumer.started",
            topic=self._topic,
            group_id=self._group_id,
        )

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            logger.info("kafka.consumer.stopped", topic=self._topic)

    async def consume(
        self,
        handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """Consume messages and process with the given handler.

        Commits offset only after successful processing. Failed messages
        are logged but not committed, allowing retry on restart.

        Args:
            handler: Async function to process each deserialized message.
        """
        if not self._consumer:
            raise RuntimeError("Consumer not started. Call start() first.")

        logger.info("kafka.consumer.polling", topic=self._topic)
        try:
            async for message in self._consumer:
                if not self._running:
                    break

                delivery_id = "unknown"
                try:
                    payload = message.value
                    delivery_id = payload.get("delivery_id", "unknown")
                    logger.info(
                        "kafka.message.received",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset,
                        delivery_id=delivery_id,
                    )

                    await handler(payload)

                    # Commit only after successful processing
                    await self._consumer.commit()
                    logger.info(
                        "kafka.message.committed",
                        topic=message.topic,
                        offset=message.offset,
                        delivery_id=delivery_id,
                    )
                except Exception:
                    logger.exception(
                        "kafka.message.processing_failed",
                        topic=message.topic,
                        offset=message.offset,
                        delivery_id=delivery_id,
                    )
                    # Don't commit — message will be retried on restart
        except Exception:
            logger.exception("kafka.consumer.fatal_error", topic=self._topic)
            raise
