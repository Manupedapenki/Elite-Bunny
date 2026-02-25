"""LLM analysis completions endpoint."""
from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from ..config import Settings
from ..prompts.builder import PromptBuilder
from ..prompts.registry import PromptRegistry
from ..providers.claude import ClaudeProvider

logger = structlog.get_logger()
settings = Settings()

router = APIRouter(tags=["completions"])

# Initialize provider and registry
provider = ClaudeProvider(
    api_key=settings.anthropic_api_key,
    default_model=settings.default_model,
    timeout=settings.request_timeout_seconds,
)
registry = PromptRegistry(prompts_dir=settings.prompts_dir)
builder = PromptBuilder()


class AnalyzeRequest(BaseModel):
    """Request schema for /analyze endpoint."""

    analysis_type: str  # "security_review" or "pr_summary"
    prompt_version: str = "1.0"
    variables: dict[str, Any]


class AnalyzeResponse(BaseModel):
    """Response schema for /analyze endpoint."""

    result: dict[str, Any]
    model: str
    tokens_used: int
    latency_ms: int
    prompt_version: str


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Run an LLM analysis using the specified prompt template.

    Loads the prompt template, substitutes variables, calls Claude API,
    and returns the parsed JSON response.
    """
    start = time.time()
    delivery_id = request.variables.get("delivery_id", "unknown")

    logger.info(
        "llm.analyze.start",
        analysis_type=request.analysis_type,
        prompt_version=request.prompt_version,
        delivery_id=delivery_id,
    )

    # Load and build prompt
    template = registry.get_template(request.analysis_type, request.prompt_version)
    system_prompt, user_prompt = builder.build(template, request.variables)

    # Call Claude API
    result = await provider.complete(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=template.get("model", settings.default_model),
        max_tokens=template.get("max_tokens", 4096),
        temperature=template.get("temperature", 0.1),
    )

    latency_ms = int((time.time() - start) * 1000)

    logger.info(
        "llm.analyze.complete",
        analysis_type=request.analysis_type,
        tokens_used=result["tokens_used"],
        latency_ms=latency_ms,
        delivery_id=delivery_id,
    )

    return AnalyzeResponse(
        result=result["content"],
        model=result["model"],
        tokens_used=result["tokens_used"],
        latency_ms=latency_ms,
        prompt_version=request.prompt_version,
    )


@router.get("/prompts")
async def list_prompts() -> dict[str, Any]:
    """List all available prompt templates and versions."""
    return {"prompts": registry.list_templates()}
