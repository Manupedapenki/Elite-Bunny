"""Kafka consumer handler for PR events — fetches diffs and enriches with context."""
from __future__ import annotations

from typing import Any

import structlog

from common.models.pr_event import PREventPayload

from .config import Settings
from .context_builder import ContextBuilder
from .chunker import DiffChunker
from .diff_parser import DiffParser
from .producer import publish_diff_context

logger = structlog.get_logger()
settings = Settings()


async def handle_pr_event(payload: dict[str, Any]) -> None:
    """Process a PR event from Kafka: fetch diff, enrich, and publish.

    Args:
        payload: Deserialized PREventPayload dict from Kafka.
    """
    event = PREventPayload.model_validate(payload)
    delivery_id = event.delivery_id

    logger.info(
        "diff_context.processing",
        delivery_id=delivery_id,
        repo=event.repository_full_name,
        pr_number=event.pr_number,
    )

    # Initialize helpers
    context_builder = ContextBuilder(settings)
    diff_parser = DiffParser()
    chunker = DiffChunker(settings)

    try:
        # Fetch the PR files and build enriched context
        file_changes = await context_builder.build_context(
            installation_id=event.installation_id,
            owner=event.repository_owner,
            repo=event.repository_name,
            pr_number=event.pr_number,
            head_sha=event.head_sha,
        )

        # Calculate totals
        total_additions = sum(f.additions for f in file_changes)
        total_deletions = sum(f.deletions for f in file_changes)

        # Chunk if needed
        chunks = chunker.chunk_files(file_changes)

        for chunk_index, chunk_files in enumerate(chunks):
            await publish_diff_context(
                event=event,
                files=chunk_files,
                total_additions=total_additions,
                total_deletions=total_deletions,
                total_files_changed=len(file_changes),
                is_chunked=len(chunks) > 1,
                chunk_index=chunk_index,
                total_chunks=len(chunks),
            )

        logger.info(
            "diff_context.completed",
            delivery_id=delivery_id,
            files_processed=len(file_changes),
            chunks=len(chunks),
        )

    except Exception:
        logger.exception(
            "diff_context.failed",
            delivery_id=delivery_id,
            repo=event.repository_full_name,
            pr_number=event.pr_number,
        )
        raise
