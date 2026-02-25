"""Confidence filter — filters out low-confidence findings before posting."""
from __future__ import annotations

import structlog

from common.models.analysis import SecurityFinding

logger = structlog.get_logger()


class ConfidenceFilter:
    """Filters security findings by confidence threshold.

    Findings below the threshold are stored in the database for analysis
    but NOT posted as GitHub comments to avoid noise.
    """

    def __init__(self, threshold: float = 0.6) -> None:
        self._threshold = threshold

    def filter(self, findings: list[SecurityFinding]) -> list[SecurityFinding]:
        """Filter findings by confidence threshold.

        Args:
            findings: All security findings from LLM analysis.

        Returns:
            Findings with confidence >= threshold.
        """
        filtered = [f for f in findings if f.confidence >= self._threshold]

        dropped = len(findings) - len(filtered)
        if dropped > 0:
            logger.info(
                "confidence.filtered",
                total=len(findings),
                passed=len(filtered),
                dropped=dropped,
                threshold=self._threshold,
            )

        return filtered
