"""Security analyzer — calls LLM service with security review prompt."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class SecurityAnalyzer:
    """Runs security-focused LLM analysis on a PR diff.

    Calls the LLM service with the security_review prompt template
    and returns the structured analysis response.
    """

    def __init__(self, llm_service_url: str) -> None:
        self._llm_service_url = llm_service_url

    async def analyze(self, variables: dict[str, Any]) -> dict[str, Any]:
        """Run security analysis via LLM service.

        Args:
            variables: Template variables including diff_content, surrounding_context, etc.

        Returns:
            Dict with keys: content, model, tokens_used.
        """
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self._llm_service_url}/analyze",
                json={
                    "analysis_type": "security_review",
                    "prompt_version": "1.0",
                    "variables": variables,
                },
            )
            response.raise_for_status()

        result = response.json()
        logger.info(
            "security_analysis.complete",
            tokens_used=result.get("tokens_used", 0),
            latency_ms=result.get("latency_ms", 0),
        )
        return {
            "content": result.get("result", {}),
            "tokens_used": result.get("tokens_used", 0),
            "model": result.get("model", "unknown"),
        }
