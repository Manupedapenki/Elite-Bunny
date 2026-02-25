"""Full pipeline integration test.

Tests the complete flow from webhook reception through to
comment formatting, mocking external services (GitHub API, Claude API).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


class TestFullPipeline:
    """Test the complete analysis pipeline with mocked externals."""

    def test_pr_event_to_diff_context_model(self):
        """Verify PREventPayload can be converted to a DiffContext request."""
        from common.models.pr_event import PREventPayload
        from common.models.diff_context import DiffContext, FileChange

        webhook = load_fixture("sample_pr_webhook.json")
        pr_data = webhook["pull_request"]
        repo_data = webhook["repository"]

        # Simulate what the webhook handler does
        event = PREventPayload(
            delivery_id="pipeline-test-001",
            action="opened",
            installation_id=webhook["installation"]["id"],
            repository_id=repo_data["id"],
            repository_full_name=repo_data["full_name"],
            repository_owner=repo_data["owner"]["login"],
            repository_name=repo_data["name"],
            repository_default_branch=repo_data.get("default_branch", "main"),
            pr_number=pr_data["number"],
            pr_title=pr_data["title"],
            pr_description=pr_data.get("body"),
            pr_author=pr_data["user"]["login"],
            head_sha=pr_data["head"]["sha"],
            base_branch=pr_data["base"]["ref"],
            head_branch=pr_data["head"]["ref"],
            pr_url=pr_data["html_url"],
            diff_url=pr_data["diff_url"],
        )

        # Simulate what the diff-context-service would produce
        sample_patch = Path(FIXTURES_DIR / "sample_diff.patch").read_text()
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
            files=[
                FileChange(
                    file_path="auth/login.py",
                    status="added",
                    additions=35,
                    deletions=0,
                    patch=sample_patch,
                    language="python",
                    surrounding_context=None,
                )
            ],
            total_additions=35,
            total_deletions=0,
            total_files_changed=1,
        )

        assert diff_context.delivery_id == "pipeline-test-001"
        assert len(diff_context.files) == 1
        assert diff_context.files[0].language == "python"

        # Verify it serializes cleanly for Kafka
        serialized = diff_context.model_dump(mode="json")
        assert isinstance(serialized, dict)
        assert serialized["pr_number"] == 42

        # Verify it deserializes back correctly
        restored = DiffContext.model_validate(serialized)
        assert restored.pr_number == diff_context.pr_number
        assert len(restored.files) == 1

    def test_analysis_result_to_notification(self):
        """Verify AnalysisResult correctly flows into notification formatters."""
        from common.models.analysis import AnalysisResult, SecurityFinding, Severity
        from notification_service.formatters.inline_comment import InlineCommentFormatter
        from notification_service.formatters.summary_comment import SummaryCommentFormatter

        llm_response = load_fixture("sample_llm_response.json")

        # Build findings from LLM response
        findings = []
        for issue in llm_response["issues"]:
            findings.append(SecurityFinding(
                severity=Severity(issue["severity"]),
                file_path=issue["file_path"],
                line_number=issue["line_number"],
                end_line_number=issue.get("end_line_number"),
                title=issue["title"],
                description=issue["description"],
                confidence=issue["confidence"],
                category=issue.get("category"),
                cwe_id=issue.get("cwe_id"),
                suggestion=issue.get("suggestion"),
            ))

        # Build full analysis result
        result = AnalysisResult(
            delivery_id="pipeline-test-001",
            installation_id=987654,
            repository_full_name="test-org/test-repo",
            pr_number=42,
            head_sha="abc123def456789012345678901234567890abcd",
            pr_title="Add user authentication endpoint",
            pr_description="JWT auth endpoints",
            security_findings=findings,
            pr_summary="This PR adds a login endpoint and JWT token generation.",
            overall_risk_score=llm_response["overall_risk_score"],
            prompt_version="1.0",
            llm_model="claude-sonnet-4-6",
            llm_tokens_used=3500,
            processing_time_ms=12000,
        )

        # Verify inline comments
        inline_formatter = InlineCommentFormatter()
        inline_comments = inline_formatter.format(result.security_findings)

        assert len(inline_comments) == 3
        assert inline_comments[0]["path"] == "auth/login.py"
        assert inline_comments[0]["line"] == 17
        assert "CRITICAL" in inline_comments[0]["body"]

        # Verify summary comment
        summary_formatter = SummaryCommentFormatter()
        summary_body = summary_formatter.format(result)

        assert "PR Intelligence Review" in summary_body
        assert "3 issues found" in summary_body
        assert "0.85" in summary_body
        assert "SQL injection" in summary_body
        assert "Hardcoded secret" in summary_body

    def test_kafka_serialization_roundtrip(self):
        """Verify all models survive JSON serialization roundtrip (Kafka transport)."""
        from common.models.pr_event import PREventPayload
        from common.models.diff_context import DiffContext, FileChange
        from common.models.analysis import AnalysisResult, SecurityFinding, Severity

        # PREventPayload roundtrip
        event = PREventPayload(
            delivery_id="roundtrip-test",
            action="opened",
            installation_id=123,
            repository_id=456,
            repository_full_name="org/repo",
            repository_owner="org",
            repository_name="repo",
            repository_default_branch="main",
            pr_number=1,
            pr_title="Test",
            pr_author="dev",
            head_sha="a" * 40,
            base_branch="main",
            head_branch="feature",
            pr_url="https://github.com/org/repo/pull/1",
            diff_url="https://github.com/org/repo/pull/1.diff",
        )
        event_json = json.dumps(event.model_dump(mode="json"), default=str)
        event_restored = PREventPayload.model_validate(json.loads(event_json))
        assert event_restored.delivery_id == event.delivery_id

        # DiffContext roundtrip
        diff = DiffContext(
            delivery_id="roundtrip-test",
            installation_id=123,
            repository_full_name="org/repo",
            pr_number=1,
            pr_title="Test",
            pr_author="dev",
            head_sha="a" * 40,
            base_branch="main",
            head_branch="feature",
            files=[FileChange(
                file_path="test.py", status="modified",
                additions=5, deletions=2, patch="@@ -1,3 +1,5 @@",
            )],
            total_additions=5,
            total_deletions=2,
            total_files_changed=1,
        )
        diff_json = json.dumps(diff.model_dump(mode="json"), default=str)
        diff_restored = DiffContext.model_validate(json.loads(diff_json))
        assert len(diff_restored.files) == 1

        # AnalysisResult roundtrip
        result = AnalysisResult(
            delivery_id="roundtrip-test",
            installation_id=123,
            repository_full_name="org/repo",
            pr_number=1,
            head_sha="a" * 40,
            pr_title="Test",
            security_findings=[SecurityFinding(
                severity=Severity.HIGH, file_path="x.py", line_number=10,
                title="Issue", description="Bad", confidence=0.8,
            )],
            pr_summary="Test summary",
            overall_risk_score=0.5,
            prompt_version="1.0",
            llm_model="claude-sonnet-4-6",
            llm_tokens_used=1000,
            processing_time_ms=5000,
        )
        result_json = json.dumps(result.model_dump(mode="json"), default=str)
        result_restored = AnalysisResult.model_validate(json.loads(result_json))
        assert len(result_restored.security_findings) == 1
        assert result_restored.security_findings[0].severity == Severity.HIGH
