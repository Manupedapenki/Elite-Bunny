"""Kafka producer for DiffContext — publishes enriched diffs to analysis.requests."""
from __future__ import annotations

import structlog

from common.models.diff_context import DiffContext, FileChange
from common.models.pr_event import PREventPayload

logger = structlog.get_logger()


async def publish_diff_context(
    event: PREventPayload,
    files: list[FileChange],
    total_additions: int,
    total_deletions: int,
    total_files_changed: int,
    is_chunked: bool = False,
    chunk_index: int = 0,
    total_chunks: int = 1,
) -> None:
    """Build a DiffContext message and publish to analysis.requests.

    Args:
        event: Original PR event.
        files: List of FileChange objects for this chunk.
        total_additions: Total additions across all files.
        total_deletions: Total deletions across all files.
        total_files_changed: Total files changed in the PR.
        is_chunked: Whether this is part of a chunked PR.
        chunk_index: Index of this chunk (0-based).
        total_chunks: Total number of chunks.
    """
    from .main import get_kafka_producer

    diff_context = DiffContext(
        delivery_id=event.delivery_id,
        installation_id=event.installation_id,
        repository_full_name=event.repository_full_name,
        pr_number=event.pr_number,
        pr_title=event.pr_title,
        pr_description=event.pr_description,
        pr_author=event.pr_author,
        head_sha=event.head_sha,
        base_branch=event.base_branch,
        head_branch=event.head_branch,
        files=files,
        total_additions=total_additions,
        total_deletions=total_deletions,
        total_files_changed=total_files_changed,
        is_chunked=is_chunked,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
    )

    producer = get_kafka_producer()
    await producer.send(
        topic="analysis.requests",
        value=diff_context.model_dump(mode="json"),
        key=event.repository_full_name,
    )

    logger.info(
        "diff_context.published",
        delivery_id=event.delivery_id,
        topic="analysis.requests",
        chunk=f"{chunk_index + 1}/{total_chunks}",
        files_in_chunk=len(files),
    )
