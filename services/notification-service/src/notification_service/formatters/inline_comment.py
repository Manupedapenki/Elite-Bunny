"""Inline comment formatter — formats security findings as GitHub review comments."""
from __future__ import annotations

from typing import Any

from common.models.analysis import SecurityFinding, Severity

# Severity emoji badges
SEVERITY_BADGES = {
    Severity.CRITICAL: "🔴 **CRITICAL**",
    Severity.HIGH: "🟠 **HIGH**",
    Severity.MEDIUM: "🟡 **MEDIUM**",
    Severity.LOW: "🔵 **LOW**",
}


class InlineCommentFormatter:
    """Formats security findings as GitHub Pull Request Review inline comments."""

    def format(self, findings: list[SecurityFinding]) -> list[dict[str, Any]]:
        """Format findings as GitHub inline review comment dicts.

        Args:
            findings: Security findings to format.

        Returns:
            List of comment dicts compatible with GitHub Review API:
            [{path, line, body, side}]
        """
        comments: list[dict[str, Any]] = []
        for finding in findings:
            body = self._format_single(finding)
            comment: dict[str, Any] = {
                "path": finding.file_path,
                "line": finding.line_number,
                "body": body,
                "side": "RIGHT",
            }
            comments.append(comment)
        return comments

    def _format_single(self, finding: SecurityFinding) -> str:
        """Format a single finding as a markdown comment body."""
        badge = SEVERITY_BADGES.get(finding.severity, "⚪ **INFO**")

        parts = [
            f"{badge} — {finding.title}",
            "",
            finding.description,
        ]

        if finding.category:
            parts.append(f"\n**Category:** `{finding.category}`")
        if finding.cwe_id:
            parts.append(f"**CWE:** [{finding.cwe_id}](https://cwe.mitre.org/data/definitions/{finding.cwe_id.replace('CWE-', '')}.html)")
        if finding.suggestion:
            parts.append(f"\n💡 **Suggested fix:** {finding.suggestion}")

        parts.append(f"\n*Confidence: {finding.confidence:.0%}*")

        return "\n".join(parts)
