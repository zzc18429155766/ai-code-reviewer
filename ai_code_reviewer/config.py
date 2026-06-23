"""Configuration management."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ReviewConfig:
    """Configuration for the code reviewer."""

    # AI settings
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: int = 4096

    # Review settings
    categories: list[str] = field(default_factory=lambda: [
        "quality", "security", "performance", "style", "bug", "maintainability"
    ])
    severity_threshold: str = "info"  # minimum severity to report
    max_files: int = 50
    max_file_size: int = 100_000  # bytes
    ignore_patterns: list[str] = field(default_factory=lambda: [
        "*.min.js", "*.min.css", "*.map", "*.lock",
        "node_modules/*", ".git/*", "__pycache__/*",
        "*.pyc", ".venv/*", "venv/*", "dist/*", "build/*",
    ])

    # Output settings
    output_format: str = "text"  # text, json, markdown
    show_suggestions: bool = True
    color: bool = True

    # GitHub Action settings
    github_token: str = ""
    pr_number: int | None = None
    repo: str = ""
    fail_on_critical: bool = False
    fail_threshold: int = 50  # minimum score to pass

    @classmethod
    def from_file(cls, path: str | Path) -> ReviewConfig:
        """Load config from a YAML file."""
        config = cls()
        p = Path(path)
        if p.exists():
            with open(p) as f:
                data = yaml.safe_load(f) or {}
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        return config

    @classmethod
    def from_env(cls) -> ReviewConfig:
        """Load config from environment variables."""
        config = cls()
        config.api_key = os.environ.get("OPENAI_API_KEY", os.environ.get("AI_REVIEWER_API_KEY", ""))
        config.api_base = os.environ.get("OPENAI_API_BASE", os.environ.get("AI_REVIEWER_API_BASE", config.api_base))
        config.model = os.environ.get("AI_REVIEWER_MODEL", config.model)
        config.github_token = os.environ.get("GITHUB_TOKEN", "")
        config.repo = os.environ.get("GITHUB_REPOSITORY", "")

        if pr := os.environ.get("GITHUB_EVENT_PULL_REQUEST_NUMBER"):
            config.pr_number = int(pr)

        return config

    @classmethod
    def load(cls, config_file: str | None = None) -> ReviewConfig:
        """Load config from file + env, with env taking precedence."""
        config_path = config_file or ".ai-reviewer.yml"
        config = cls.from_file(config_path)

        # Override with env
        env_config = cls.from_env()
        for field_name in [
            "api_key", "api_base", "model", "github_token", "repo", "pr_number"
        ]:
            env_val = getattr(env_config, field_name)
            if env_val:
                setattr(config, field_name, env_val)

        return config


SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
