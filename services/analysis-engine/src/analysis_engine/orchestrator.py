"""Analysis orchestrator — coordinates security and summary LLM analysis."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog

from common.models.analysis import AnalysisResult, SecurityFinding
from common.models.diff_context import DiffContext

from .analyzers.security_analyzer import SecurityAnalyzer
from .analyzers.summary_analyzer import SummaryAnalyzer
from .config import Settings
from .parsers.llm_response_parser import LLMResponseParser
from .scoring.confidence import ConfidenceFilter

logger = structlog.get_logger()


class AnalysisOrchestrator:
    """Orchestrates concurrent security and summary LLM analysis.

    Coordinates two LLM calls (security review + PR summary),
    parses results, filters by confidence, and publishes to Kafka.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._security_analyzer = SecurityAnalyzer(settings.llm_service_url)
        self._summary_analyzer = SummaryAnalyzer(settings.llm_service_url)
        self._parser = LLMResponseParser()
        self._confidence_filter = ConfidenceFilter(settings.confidence_threshold)

    async def analyze(self, diff_context: DiffContext) -> None:
        """Run full analysis pipeline on a diff context.

        Steps:
        1. Build diff content string from file changes
        2. Run security + summary analysis concurrently
        3. Parse and filter results
        4. Publish AnalysisResult to Kafka

        Args:
            diff_context: Enriched diff context from diff-context-service.
        """
        start_time = time.time()
        delivery_id = diff_context.delivery_id

        # Build content strings for LLM
        diff_content = self._build_diff_content(diff_context)
        surrounding_context = self._build_surrounding_context(diff_context)

        variables = {
            "pr_title": diff_context.pr_title,
            "pr_description": diff_context.pr_description or "No description provided",
            "pr_author": diff_context.pr_author,
            "head_branch": diff_context.head_branch,
            "base_branch": diff_context.base_branch,
            "total_files_changed": diff_context.total_files_changed,
            "total_additions": diff_context.total_additions,
            "total_deletions": diff_context.total_deletions,
            "diff_content": diff_content,
            "surrounding_context": surrounding_context,
        }

        # Run both analyses concurrently
        try:
            security_result, summary_result = await asyncio.gather(
                self._security_analyzer.analyze(variables),
                self._summary_analyzer.analyze(variables),
                return_exceptions=True,
            )
        except Exception:
            logger.exception("analysis.concurrent_failure", delivery_id=delivery_id)
            raise

        # Handle individual failures
        if isinstance(security_result, Exception):
            logger.error("analysis.security_failed", delivery_id=delivery_id, error=str(security_result))
            security_result = {"content": {"issues": [], "overall_risk_score": 0.0}, "tokens_used": 0, "model": "unknown"}

        if isinstance(summary_result, Exception):
            logger.error("analysis.summary_failed", delivery_id=delivery_id, error=str(summary_result))
            summary_result = {"content": {"summary": "Analysis failed — unable to generate summary."}, "tokens_used": 0, "model": "unknown"}

        # Parse security findings
        security_data = security_result["content"] if isinstance(security_result, dict) else security_result
        summary_data = summary_result["content"] if isinstance(summary_result, dict) else summary_result

        findings = self._parser.parse_security_findings(security_data)

        # Filter by confidence threshold
        filtered_findings = self._confidence_filter.filter(findings)

        # Calculate totals
        total_tokens = (
            (security_result.get("tokens_used", 0) if isinstance(security_result, dict) else 0)
            + (summary_result.get("tokens_used", 0) if isinstance(summary_result, dict) else 0)
        )
        model = security_result.get("model", "unknown") if isinstance(security_result, dict) else "unknown"
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Build analysis result
        analysis_result = AnalysisResult(
            delivery_id=delivery_id,
            installation_id=diff_context.installation_id,
            repository_full_name=diff_context.repository_full_name,
            pr_number=diff_context.pr_number,
            head_sha=diff_context.head_sha,
            pr_title=diff_context.pr_title,
            pr_description=diff_context.pr_description,
            security_findings=filtered_findings,
            pr_summary=summary_data.get("summary", "") if isinstance(summary_data, dict) else str(summary_data),
            overall_risk_score=security_data.get("overall_risk_score", 0.0) if isinstance(security_data, dict) else 0.0,
            prompt_version="1.0",
            llm_model=model,
            llm_tokens_used=total_tokens,
            processing_time_ms=processing_time_ms,
        )

        # Publish to Kafka
        from .main import get_kafka_producer
        producer = get_kafka_producer()
        await producer.send(
            topic="analysis.results",
            value=analysis_result.model_dump(mode="json"),
            key=diff_context.repository_full_name,
        )

        logger.info(
            "analysis.completed",
            delivery_id=delivery_id,
            findings=len(filtered_findings),
            filtered_out=len(findings) - len(filtered_findings),
            risk_score=analysis_result.overall_risk_score,
            tokens_used=total_tokens,
            processing_time_ms=processing_time_ms,
        )

    def _build_diff_content(self, diff_context: DiffContext) -> str:
        """Build a formatted diff string from file changes."""
        parts: list[str] = []
        for file in diff_context.files:
            lang = file.language or "text"
            header = f"### {file.file_path} ({file.status}, +{file.additions} -{file.deletions})"
            parts.append(f"{header}\n```{lang}\n{file.patch}\n```")
        return "\n\n".join(parts)

    def _build_surrounding_context(self, diff_context: DiffContext) -> str:
        """Build surrounding context string from file changes."""
        parts: list[str] = []
        for file in diff_context.files:
            if file.surrounding_context:
                parts.append(file.surrounding_context)
        return "\n\n".join(parts) if parts else "No surrounding context available."
