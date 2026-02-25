"""Summary comment formatter — formats PR analysis as a summary comment."""
from __future__ import annotations

from common.models.analysis import AnalysisResult, Severity

# Risk score visual indicators
RISK_INDICATORS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}


class SummaryCommentFormatter:
    """Formats a complete analysis result as a GitHub PR summary comment."""

    def format(self, result: AnalysisResult) -> str:
        """Format an AnalysisResult as a markdown summary comment.

        Includes:
        - PR summary (what does the PR do)
        - Security findings table
        - Overall risk score
        - Analysis metadata
        """
        parts: list[str] = []

        # Header
        parts.append("## 🤖 PR Intelligence Review\n")

        # Summary section
        parts.append("### Summary")
        parts.append(result.pr_summary)
        parts.append("")

        # Security findings section
        if result.security_findings:
            parts.append(f"### Security Findings ({len(result.security_findings)} issues found)\n")
            parts.append("| Severity | File | Issue |")
            parts.append("|---|---|---|")

            for finding in result.security_findings:
                badge = RISK_INDICATORS.get(finding.severity.value, "⚪")
                severity_label = finding.severity.value.upper()
                file_ref = f"`{finding.file_path}:{finding.line_number}`"
                parts.append(f"| {badge} {severity_label} | {file_ref} | {finding.title} |")

            parts.append("")
        else:
            parts.append("### Security Findings\n")
            parts.append("✅ **No security issues found.** This PR looks clean!\n")

        # Risk score
        risk_score = result.overall_risk_score
        if risk_score >= 0.7:
            risk_emoji = "🔴"
        elif risk_score >= 0.4:
            risk_emoji = "🟡"
        else:
            risk_emoji = "🟢"

        parts.append(f"### Risk Score: {risk_emoji} {risk_score:.2f} / 1.00\n")

        # Footer with metadata
        parts.append("---")
        parts.append(
            f"*Analyzed with prompt v{result.prompt_version} · "
            f"Model: {result.llm_model} · "
            f"Tokens: {result.llm_tokens_used:,} · "
            f"Time: {result.processing_time_ms:,}ms*"
        )

        return "\n".join(parts)
