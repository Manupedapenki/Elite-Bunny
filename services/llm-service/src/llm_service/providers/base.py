"""Abstract base LLM provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Send a completion request to the LLM.

        Args:
            system_prompt: System-level instruction.
            user_prompt: User-level prompt with context.
            model: Model identifier.
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.

        Returns:
            Dict with keys: content (parsed JSON), model, tokens_used.
        """
        ...
