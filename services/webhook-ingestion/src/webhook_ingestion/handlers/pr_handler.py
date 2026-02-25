"""PR event handler — parses webhook payload and publishes to Kafka."""
from __future__ import annotations

from typing import Any

import structlog

from common.models.pr_event import PREventPayload

from ..main import get_kafka_producer

logger = structlog.get_logger()


async def handle_pr_event(delivery_id: str, payload: dict[str, Any]) -> None:
    """Parse a GitHub PR webhook payload and publish to Kafka pr.events.

    Args:
        delivery_id: X-GitHub-Delivery header value.
        payload: Raw webhook JSON payload.
    """
    pr_data = payload.get("pull_request", {})
    repo_data = payload.get("repository", {})
    installation = payload.get("installation", {})

    # Build the structured PR event
    event = PREventPayload(
        delivery_id=delivery_id,
        action=payload["action"],
        installation_id=installation.get("id", 0),
        repository_id=repo_data.get("id", 0),
        repository_full_name=repo_data.get("full_name", ""),
        repository_owner=repo_data.get("owner", {}).get("login", ""),
        repository_name=repo_data.get("name", ""),
        repository_default_branch=repo_data.get("default_branch", "main"),
        pr_number=pr_data.get("number", 0),
        pr_title=pr_data.get("title", ""),
        pr_description=pr_data.get("body"),
        pr_author=pr_data.get("user", {}).get("login", ""),
        head_sha=pr_data.get("head", {}).get("sha", ""),
        base_branch=pr_data.get("base", {}).get("ref", ""),
        head_branch=pr_data.get("head", {}).get("ref", ""),
        pr_url=pr_data.get("html_url", ""),
        diff_url=pr_data.get("diff_url", ""),
    )

    logger.info(
        "pr_event.parsed",
        delivery_id=delivery_id,
        action=event.action,
        repo=event.repository_full_name,
        pr_number=event.pr_number,
        pr_title=event.pr_title,
    )

    # Publish to Kafka pr.events topic
    producer = get_kafka_producer()
    await producer.send(
        topic="pr.events",
        value=event.model_dump(mode="json"),
        key=event.repository_full_name,
    )

    logger.info(
        "pr_event.published",
        delivery_id=delivery_id,
        topic="pr.events",
    )
