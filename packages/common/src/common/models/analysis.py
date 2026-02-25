"""Pydantic models for analysis results."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Security finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SecurityFinding(BaseModel):
    """A single security finding from LLM analysis."""

    severity: Severity
    file_path: str
    line_number: int
    end_line_number: Optional[int] = None
    title: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: Optional[str] = None
    cwe_id: Optional[str] = None
    suggestion: Optional[str] = None


class PRSummaryResult(BaseModel):
    """LLM-generated PR summary."""

    summary: str
    key_changes: list[str]
    architectural_impact: str
    architectural_notes: Optional[str] = None
    testing_concerns: list[str]
    labels_suggested: list[str]


class AnalysisResult(BaseModel):
    """Complete analysis result. Published to analysis.results."""

    delivery_id: str
    installation_id: int
    repository_full_name: str
    pr_number: int
    head_sha: str
    pr_title: str
    pr_description: Optional[str] = None
    security_findings: list[SecurityFinding]
    pr_summary: str
    overall_risk_score: float = Field(..., ge=0.0, le=1.0)
    prompt_version: str
    llm_model: str
    llm_tokens_used: int
    processing_time_ms: int
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
