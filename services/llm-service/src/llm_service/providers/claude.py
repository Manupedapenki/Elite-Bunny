"""Anthropic Claude API provider."""
from __future__ import annotations

import json
import re
from typing import Any

import anthropic
import structlog

from common.exceptions import LLMResponseParseError, LLMRateLimitError, LLMTimeoutError

from .base import BaseLLMProvider

logger = structlog.get_logger()


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude API integration.

    Handles API calls, response parsing, rate limit retries,
    and JSON extraction from Claude's responses.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-sonnet-4-6",
        timeout: int = 120,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=timeout,
        )
        self._default_model = default_model

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Send a completion request to Claude API.

        Automatically parses JSON from the response and handles
        common error cases (rate limits, timeouts, malformed JSON).

        Returns:
            Dict with keys: content (parsed JSON), model, tokens_used.
        """
        model = model or self._default_model

        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )
        except anthropic.RateLimitError as e:
            logger.warning("llm.rate_limited", model=model)
            raise LLMRateLimitError(f"Claude rate limit exceeded: {e}") from e
        except anthropic.APITimeoutError as e:
            logger.warning("llm.timeout", model=model)
            raise LLMTimeoutError(f"Claude API timeout: {e}") from e

        # Extract text content
        raw_text = ""
        for block in response.content:
            if block.type == "text":
                raw_text += block.text

        # Parse JSON from response
        parsed = self._parse_json_response(raw_text)

        tokens_used = (
            (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)
        )

        logger.info(
            "llm.complete",
            model=response.model,
            tokens_used=tokens_used,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return {
            "content": parsed,
            "model": response.model,
            "tokens_used": tokens_used,
        }

    def _parse_json_response(self, raw_text: str) -> dict[str, Any]:
        """Parse JSON from LLM response text.

        Handles common cases:
        - Clean JSON
        - JSON wrapped in markdown code fences
        - JSON with leading/trailing text

        Args:
            raw_text: Raw text from LLM response.

        Returns:
            Parsed JSON as dict.

        Raises:
            LLMResponseParseError: If JSON cannot be extracted.
        """
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

        raise LLMResponseParseError(
            f"Failed to parse JSON from LLM response. Raw text: {text[:500]}"
        )
