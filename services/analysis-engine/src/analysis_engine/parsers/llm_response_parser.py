"""LLM response parser — extracts security findings from LLM JSON output."""
from __future__ import annotations

from typing import Any

import structlog

from common.models.analysis import SecurityFinding, Severity

logger = structlog.get_logger()


class LLMResponseParser:
    """Parses LLM JSON responses into typed SecurityFinding models.

    Handles malformed data gracefully — logs warnings and skips
    invalid findings rather than failing the entire analysis.
    """

    def parse_security_findings(self, data: dict[str, Any]) -> list[SecurityFinding]:
        """Parse security findings from LLM response data.

        Args:
            data: Parsed JSON dict from LLM response.

        Returns:
            List of SecurityFinding models.
        """
        issues = data.get("issues", [])
        findings: list[SecurityFinding] = []

        for i, issue in enumerate(issues):
            try:
                # Validate severity
                severity_str = issue.get("severity", "low").lower()
                if severity_str not in {"critical", "high", "medium", "low"}:
                    severity_str = "low"

                finding = SecurityFinding(
                    severity=Severity(severity_str),
                    file_path=issue.get("file_path", "unknown"),
                    line_number=issue.get("line_number", 0),
                    end_line_number=issue.get("end_line_number"),
                    title=issue.get("title", "Untitled finding"),
                    description=issue.get("description", ""),
                    confidence=max(0.0, min(1.0, float(issue.get("confidence", 0.5)))),
                    category=issue.get("category"),
                    cwe_id=issue.get("cwe_id"),
                    suggestion=issue.get("suggestion"),
                )
                findings.append(finding)
            except Exception:
                logger.warning(
                    "parser.finding_skipped",
                    index=i,
                    reason="Invalid data",
                )
                continue

        logger.info("parser.findings_parsed", count=len(findings), total_issues=len(issues))
        return findings
