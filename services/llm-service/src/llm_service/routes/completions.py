"""LLM analysis completions endpoint."""
from __future__ import annotations

import json
import re
import time
from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from ..config import Settings
from ..prompts.builder import PromptBuilder
from ..prompts.registry import PromptRegistry
from ..providers.gemini import GeminiProvider

logger = structlog.get_logger()
settings = Settings()

router = APIRouter(tags=["completions"])

# Initialize provider and registry (GeminiProvider reads GEMINI_API_KEY from env)
provider = GeminiProvider()
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


def _parse_json_response(raw_text: str) -> dict[str, Any]:
    """Parse JSON from raw LLM response text."""
    text = raw_text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try stripping markdown code fences
    code_fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(code_fence_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding JSON object in text
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Failed to parse JSON from LLM response: {text[:500]}")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Run an LLM analysis using the specified prompt template.

    Loads the prompt template, substitutes variables, calls Gemini API,
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

    # Build message list for GeminiProvider
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Call Gemini API — returns raw text
    raw_text = await provider.complete(messages)

    logger.info("llm.raw_response", raw_text_preview=raw_text[:500] if raw_text else "EMPTY")

    # Parse the JSON from Gemini's response
    try:
        parsed = _parse_json_response(raw_text)
    except Exception as exc:
        logger.error("llm.parse_failed", error=str(exc), raw_text_preview=raw_text[:500] if raw_text else "EMPTY")
        raise

    logger.info("llm.parsed_result", keys=list(parsed.keys()) if isinstance(parsed, dict) else "NOT_DICT")

    latency_ms = int((time.time() - start) * 1000)

    logger.info(
        "llm.analyze.complete",
        analysis_type=request.analysis_type,
        latency_ms=latency_ms,
        delivery_id=delivery_id,
    )

    return AnalyzeResponse(
        result=parsed,
        model="gemini-2.0-flash",
        tokens_used=0,
        latency_ms=latency_ms,
        prompt_version=request.prompt_version,
    )


@router.get("/prompts")
async def list_prompts() -> dict[str, Any]:
    """List all available prompt templates and versions."""
    return {"prompts": registry.list_templates()}
