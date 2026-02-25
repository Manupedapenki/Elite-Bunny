"""Prompt builder — assembles final prompts from templates and variables."""
from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


class PromptBuilder:
    """Builds final prompts by substituting variables into templates.

    Templates use Python format string syntax: {variable_name}.
    Missing variables are replaced with empty strings.
    """

    def build(
        self,
        template: dict[str, Any],
        variables: dict[str, Any],
    ) -> tuple[str, str]:
        """Build system and user prompts from a template.

        Args:
            template: Prompt template dict with 'system' and 'user' keys.
            variables: Variables to substitute into the template.

        Returns:
            Tuple of (system_prompt, user_prompt).
        """
        system_template = template.get("system", "")
        user_template = template.get("user", "")

        # Substitute variables, using empty string for missing keys
        safe_vars = SafeDict(variables)
        system_prompt = system_template.format_map(safe_vars)
        user_prompt = user_template.format_map(safe_vars)

        logger.debug(
            "prompt.built",
            system_length=len(system_prompt),
            user_length=len(user_prompt),
            variables_count=len(variables),
        )

        return system_prompt, user_prompt


class SafeDict(dict):
    """Dict that returns empty string for missing keys during format_map."""

    def __missing__(self, key: str) -> str:
        logger.warning("prompt.missing_variable", key=key)
        return ""
