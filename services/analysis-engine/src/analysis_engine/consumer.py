"""Kafka consumer handler for analysis requests."""
from __future__ import annotations

from typing import Any

import structlog

from common.models.diff_context import DiffContext

from .config import Settings
from .orchestrator import AnalysisOrchestrator

logger = structlog.get_logger()
settings = Settings()


async def handle_analysis_request(payload: dict[str, Any]) -> None:
    """Process an analysis request from Kafka.

    Deserializes the DiffContext, runs security + summary analysis
    concurrently, and publishes results.

    Args:
        payload: Deserialized DiffContext dict from Kafka.
    """
    diff_context = DiffContext.model_validate(payload)
    delivery_id = diff_context.delivery_id

    logger.info(
        "analysis.processing",
        delivery_id=delivery_id,
        repo=diff_context.repository_full_name,
        pr_number=diff_context.pr_number,
        files=diff_context.total_files_changed,
    )

    orchestrator = AnalysisOrchestrator(settings)
    await orchestrator.analyze(diff_context)
