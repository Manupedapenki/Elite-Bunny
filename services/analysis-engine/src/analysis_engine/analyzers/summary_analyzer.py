"""Summary analyzer — calls LLM service with PR summary prompt."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class SummaryAnalyzer:
    """Runs PR summary LLM analysis to generate a human-readable summary.

    Calls the LLM service with the pr_summary prompt template.
    """

    def __init__(self, llm_service_url: str) -> None:
        self._llm_service_url = llm_service_url

    async def analyze(self, variables: dict[str, Any]) -> dict[str, Any]:
        """Run PR summary analysis via LLM service.

        Args:
            variables: Template variables including diff_content, pr_title, etc.

        Returns:
            Dict with keys: content, model, tokens_used.
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._llm_service_url}/analyze",
                json={
                    "analysis_type": "pr_summary",
                    "prompt_version": "1.0",
                    "variables": variables,
                },
            )
            response.raise_for_status()

        result = response.json()
        logger.info(
            "summary_analysis.complete",
            tokens_used=result.get("tokens_used", 0),
            latency_ms=result.get("latency_ms", 0),
        )
        return {
            "content": result.get("result", {}),
            "tokens_used": result.get("tokens_used", 0),
            "model": result.get("model", "unknown"),
        }
