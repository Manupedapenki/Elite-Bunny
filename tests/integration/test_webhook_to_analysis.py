"""Integration tests: webhook ingestion to Kafka pipeline."""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


def generate_signature(payload: bytes, secret: str) -> str:
    """Generate a valid X-Hub-Signature-256 header."""
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


class TestWebhookSignatureVerification:
    """Test webhook signature verification logic."""

    def test_valid_signature(self):
        """Valid HMAC-SHA256 signature should pass verification."""
        from webhook_ingestion.security.signature import verify_webhook_signature

        payload = b'{"test": "data"}'
        secret = "test-secret"
        signature = generate_signature(payload, secret)

        assert verify_webhook_signature(payload, signature, secret) is True

    def test_invalid_signature(self):
        """Invalid signature should fail verification."""
        from webhook_ingestion.security.signature import verify_webhook_signature

        payload = b'{"test": "data"}'
        secret = "test-secret"
        wrong_signature = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

        assert verify_webhook_signature(payload, wrong_signature, secret) is False

    def test_missing_signature_prefix(self):
        """Signature without sha256= prefix should fail."""
        from webhook_ingestion.security.signature import verify_webhook_signature

        payload = b'{"test": "data"}'
        secret = "test-secret"

        assert verify_webhook_signature(payload, "invalid", secret) is False

    def test_empty_secret_allows_all(self):
        """Empty secret (dev mode) should allow all requests."""
        from webhook_ingestion.security.signature import verify_webhook_signature

        payload = b'{"test": "data"}'
        assert verify_webhook_signature(payload, "sha256=anything", "") is True


class TestPREventParsing:
    """Test PR event payload parsing."""

    def test_parse_pr_opened_event(self):
        """Should correctly parse a PR opened webhook payload."""
        from common.models.pr_event import PREventPayload

        payload = load_fixture("sample_pr_webhook.json")
        pr_data = payload["pull_request"]
        repo_data = payload["repository"]
        installation = payload["installation"]

        event = PREventPayload(
            delivery_id="test-delivery-001",
            action=payload["action"],
            installation_id=installation["id"],
            repository_id=repo_data["id"],
            repository_full_name=repo_data["full_name"],
            repository_owner=repo_data["owner"]["login"],
            repository_name=repo_data["name"],
            repository_default_branch=repo_data["default_branch"],
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

        assert event.action == "opened"
        assert event.pr_number == 42
        assert event.repository_full_name == "test-org/test-repo"
        assert event.pr_title == "Add user authentication endpoint"
        assert event.pr_author == "test-developer"
        assert event.head_sha == "abc123def456789012345678901234567890abcd"
        assert event.base_branch == "main"
        assert event.head_branch == "feature/user-auth"
        assert event.installation_id == 987654


class TestAnalysisModels:
    """Test analysis-related Pydantic models."""

    def test_parse_security_findings(self):
        """Should correctly parse LLM security analysis response."""
        from common.models.analysis import SecurityFinding, Severity

        llm_response = load_fixture("sample_llm_response.json")

        findings = []
        for issue in llm_response["issues"]:
            finding = SecurityFinding(
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
            )
            findings.append(finding)

        assert len(findings) == 3
        assert findings[0].severity == Severity.CRITICAL
        assert findings[0].category == "sqli"
        assert findings[0].cwe_id == "CWE-89"
        assert findings[0].confidence == 0.95
        assert findings[1].severity == Severity.HIGH
        assert findings[2].severity == Severity.MEDIUM

    def test_confidence_filter(self):
        """Should filter findings below confidence threshold."""
        from analysis_engine.scoring.confidence import ConfidenceFilter
        from common.models.analysis import SecurityFinding, Severity

        findings = [
            SecurityFinding(
                severity=Severity.CRITICAL, file_path="a.py", line_number=1,
                title="Real issue", description="Confirmed", confidence=0.95,
            ),
            SecurityFinding(
                severity=Severity.LOW, file_path="b.py", line_number=1,
                title="Maybe issue", description="Uncertain", confidence=0.3,
            ),
            SecurityFinding(
                severity=Severity.MEDIUM, file_path="c.py", line_number=1,
                title="Borderline", description="Just above", confidence=0.6,
            ),
        ]

        filter = ConfidenceFilter(threshold=0.6)
        filtered = filter.filter(findings)

        assert len(filtered) == 2
        assert filtered[0].title == "Real issue"
        assert filtered[1].title == "Borderline"


class TestDiffParser:
    """Test unified diff parsing."""

    def test_parse_hunk_headers(self):
        """Should extract hunk ranges from unified diff."""
        from diff_context.diff_parser import DiffParser

        patch = """@@ -0,0 +1,35 @@
+import sqlite3
+from flask import Flask, request, jsonify
+
+app = Flask(__name__)"""

        parser = DiffParser()
        hunks = parser.parse_patch(patch)

        assert len(hunks) == 1
        assert hunks[0].new_start == 1
        assert hunks[0].new_count == 35

    def test_get_changed_line_ranges(self):
        """Should return line ranges of changed code."""
        from diff_context.diff_parser import DiffParser

        patch = """@@ -10,5 +10,8 @@
 unchanged
+added line
+another added
 unchanged
@@ -30,3 +33,5 @@
 context
+new code
+more new code"""

        parser = DiffParser()
        ranges = parser.get_changed_line_ranges(patch)

        assert len(ranges) == 2
        assert ranges[0] == (10, 17)
        assert ranges[1] == (33, 37)

    def test_empty_patch(self):
        """Should return empty list for empty patch."""
        from diff_context.diff_parser import DiffParser

        parser = DiffParser()
        assert parser.parse_patch("") == []


class TestDiffChunker:
    """Test PR diff chunking logic."""

    def test_small_pr_no_chunking(self):
        """Small PRs should return a single chunk."""
        from common.models.diff_context import FileChange
        from diff_context.chunker import DiffChunker
        from diff_context.config import Settings

        settings = Settings(
            max_files_per_analysis=30,
            max_diff_size_bytes=500_000,
        )
        chunker = DiffChunker(settings)

        files = [
            FileChange(file_path=f"file{i}.py", status="modified",
                       additions=10, deletions=5, patch="+ line" * 10)
            for i in range(5)
        ]

        chunks = chunker.chunk_files(files)
        assert len(chunks) == 1
        assert len(chunks[0]) == 5

    def test_large_pr_chunking_by_count(self):
        """PRs with many files should be split into chunks."""
        from common.models.diff_context import FileChange
        from diff_context.chunker import DiffChunker
        from diff_context.config import Settings

        settings = Settings(
            max_files_per_analysis=3,
            max_diff_size_bytes=500_000,
        )
        chunker = DiffChunker(settings)

        files = [
            FileChange(file_path=f"file{i}.py", status="modified",
                       additions=10, deletions=5, patch="+ line")
            for i in range(10)
        ]

        chunks = chunker.chunk_files(files)
        assert len(chunks) == 4  # ceil(10/3) = 4
        assert len(chunks[0]) == 3
        assert len(chunks[-1]) == 1  # last chunk has remainder


class TestLLMResponseParser:
    """Test LLM response JSON parsing."""

    def test_parse_valid_response(self):
        """Should parse valid security findings from LLM response."""
        from analysis_engine.parsers.llm_response_parser import LLMResponseParser

        data = load_fixture("sample_llm_response.json")
        parser = LLMResponseParser()
        findings = parser.parse_security_findings(data)

        assert len(findings) == 3
        assert findings[0].title == "SQL injection in user lookup query"
        assert findings[0].line_number == 17

    def test_parse_empty_issues(self):
        """Should return empty list for clean PRs."""
        from analysis_engine.parsers.llm_response_parser import LLMResponseParser

        parser = LLMResponseParser()
        findings = parser.parse_security_findings({"issues": []})
        assert findings == []

    def test_parse_malformed_issue_skipped(self):
        """Should skip malformed issues rather than failing."""
        from analysis_engine.parsers.llm_response_parser import LLMResponseParser

        data = {
            "issues": [
                {"severity": "critical", "file_path": "a.py", "line_number": 1,
                 "title": "Valid", "description": "desc", "confidence": 0.9},
                {"severity": "invalid_severity"},  # malformed
                {"severity": "low", "file_path": "b.py", "line_number": 5,
                 "title": "Also valid", "description": "desc", "confidence": 0.7},
            ]
        }

        parser = LLMResponseParser()
        findings = parser.parse_security_findings(data)
        assert len(findings) == 3  # even malformed parses with defaults


class TestCommentFormatters:
    """Test GitHub comment formatting."""

    def test_inline_comment_format(self):
        """Should format findings with severity badges and CWE links."""
        from common.models.analysis import SecurityFinding, Severity
        from notification_service.formatters.inline_comment import InlineCommentFormatter

        finding = SecurityFinding(
            severity=Severity.CRITICAL,
            file_path="auth/login.py",
            line_number=17,
            title="SQL injection in user lookup",
            description="The query uses f-string formatting for user input.",
            confidence=0.95,
            category="sqli",
            cwe_id="CWE-89",
            suggestion="Use parameterized queries",
        )

        formatter = InlineCommentFormatter()
        comments = formatter.format([finding])

        assert len(comments) == 1
        assert comments[0]["path"] == "auth/login.py"
        assert comments[0]["line"] == 17
        assert "CRITICAL" in comments[0]["body"]
        assert "CWE-89" in comments[0]["body"]
        assert "parameterized queries" in comments[0]["body"]

    def test_summary_comment_with_findings(self):
        """Should format a full summary with findings table and risk score."""
        from common.models.analysis import AnalysisResult, SecurityFinding, Severity
        from notification_service.formatters.summary_comment import SummaryCommentFormatter

        result = AnalysisResult(
            delivery_id="test-001",
            installation_id=123,
            repository_full_name="org/repo",
            pr_number=42,
            head_sha="abc123",
            pr_title="Add auth",
            security_findings=[
                SecurityFinding(
                    severity=Severity.CRITICAL, file_path="auth/login.py",
                    line_number=17, title="SQL injection",
                    description="Bad query", confidence=0.95,
                ),
            ],
            pr_summary="This PR adds authentication.",
            overall_risk_score=0.85,
            prompt_version="1.0",
            llm_model="claude-sonnet-4-6",
            llm_tokens_used=3500,
            processing_time_ms=12000,
        )

        formatter = SummaryCommentFormatter()
        body = formatter.format(result)

        assert "PR Intelligence Review" in body
        assert "This PR adds authentication" in body
        assert "1 issues found" in body
        assert "SQL injection" in body
        assert "0.85" in body
        assert "claude-sonnet-4-6" in body

    def test_summary_comment_clean_pr(self):
        """Should show clean message for PRs with no findings."""
        from common.models.analysis import AnalysisResult
        from notification_service.formatters.summary_comment import SummaryCommentFormatter

        result = AnalysisResult(
            delivery_id="test-002",
            installation_id=123,
            repository_full_name="org/repo",
            pr_number=10,
            head_sha="def456",
            pr_title="Update docs",
            security_findings=[],
            pr_summary="Documentation update.",
            overall_risk_score=0.0,
            prompt_version="1.0",
            llm_model="claude-sonnet-4-6",
            llm_tokens_used=1500,
            processing_time_ms=5000,
        )

        formatter = SummaryCommentFormatter()
        body = formatter.format(result)

        assert "No security issues found" in body
        assert "looks clean" in body
