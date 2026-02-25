"""Kafka consumer handler for analysis results — formats and posts to GitHub."""
from __future__ import annotations

from typing import Any

import structlog

from common.models.analysis import AnalysisResult

from .config import Settings
from .formatters.inline_comment import InlineCommentFormatter
from .formatters.summary_comment import SummaryCommentFormatter
from .publishers.github_publisher import GitHubPublisher

logger = structlog.get_logger()
settings = Settings()


async def handle_analysis_result(payload: dict[str, Any]) -> None:
    """Process an analysis result: format and post comments to GitHub PR.

    Args:
        payload: Deserialized AnalysisResult dict from Kafka.
    """
    result = AnalysisResult.model_validate(payload)
    delivery_id = result.delivery_id

    logger.info(
        "notification.processing",
        delivery_id=delivery_id,
        repo=result.repository_full_name,
        pr_number=result.pr_number,
        findings=len(result.security_findings),
    )

    # Format comments
    inline_formatter = InlineCommentFormatter()
    summary_formatter = SummaryCommentFormatter()

    inline_comments = inline_formatter.format(result.security_findings)
    summary_body = summary_formatter.format(result)

    # Publish to GitHub
    publisher = GitHubPublisher(settings)

    try:
        # Post inline review comments (if any findings)
        if inline_comments:
            await publisher.post_review(
                installation_id=result.installation_id,
                repository_full_name=result.repository_full_name,
                pr_number=result.pr_number,
                head_sha=result.head_sha,
                comments=inline_comments,
            )

        # Always post summary comment
        await publisher.post_summary(
            installation_id=result.installation_id,
            repository_full_name=result.repository_full_name,
            pr_number=result.pr_number,
            body=summary_body,
        )

        logger.info(
            "notification.completed",
            delivery_id=delivery_id,
            inline_comments=len(inline_comments),
        )
    except Exception:
        logger.exception(
            "notification.failed",
            delivery_id=delivery_id,
            repo=result.repository_full_name,
            pr_number=result.pr_number,
        )
        raise
