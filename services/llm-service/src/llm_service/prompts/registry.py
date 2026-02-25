"""Prompt template registry — loads and versions YAML prompt files."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
import structlog

logger = structlog.get_logger()


class PromptRegistry:
    """Loads prompt templates from YAML files and provides versioned access.

    Templates are stored as YAML files with naming convention:
    {analysis_type}_v{version}.yaml

    Example: security_review_v1.yaml, pr_summary_v1.yaml
    """

    def __init__(self, prompts_dir: str = "/app/prompts") -> None:
        self._prompts_dir = Path(prompts_dir)
        self._templates: dict[str, dict[str, Any]] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all YAML prompt templates from the prompts directory."""
        if not self._prompts_dir.exists():
            # Try relative path for local dev
            alt_path = Path(__file__).parent.parent.parent.parent.parent / "prompts"
            if alt_path.exists():
                self._prompts_dir = alt_path
            else:
                logger.warning("prompts.dir_not_found", path=str(self._prompts_dir))
                return

        for yaml_file in self._prompts_dir.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    template = yaml.safe_load(f)

                # Extract name and version from filename (e.g., security_review_v1.yaml)
                stem = yaml_file.stem  # e.g., "security_review_v1"
                parts = stem.rsplit("_v", 1)
                if len(parts) == 2:
                    name, version = parts[0], parts[1]
                else:
                    name, version = stem, "1"

                key = f"{name}:{version}"
                template["_name"] = name
                template["_version"] = version
                self._templates[key] = template

                logger.info("prompts.loaded", name=name, version=version)
            except Exception:
                logger.exception("prompts.load_error", file=str(yaml_file))

    def get_template(self, analysis_type: str, version: str = "1.0") -> dict[str, Any]:
        """Get a prompt template by analysis type and version.

        Args:
            analysis_type: Type of analysis (e.g., "security_review", "pr_summary").
            version: Template version (e.g., "1.0").

        Returns:
            Template dict with system, user, model, etc.
        """
        # Try exact version match
        # Convert version format: "1.0" -> "1"
        short_version = version.split(".")[0] if "." in version else version
        key = f"{analysis_type}:{short_version}"

        if key in self._templates:
            return self._templates[key]

        # Try with full version
        key_full = f"{analysis_type}:{version}"
        if key_full in self._templates:
            return self._templates[key_full]

        available = list(self._templates.keys())
        raise KeyError(
            f"Prompt template not found: {analysis_type} v{version}. "
            f"Available: {available}"
        )

    def list_templates(self) -> list[dict[str, str]]:
        """List all available prompt templates."""
        return [
            {"name": t["_name"], "version": t["_version"]}
            for t in self._templates.values()
        ]
