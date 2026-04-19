"""Load per-repository configuration from .github/ai-gate.yml."""

from __future__ import annotations

import logging

import yaml
from pydantic import ValidationError

from src.domain.interfaces import IConfigLoader, IGitHubClient

from .schema import AppConfig

__all__ = ["GitHubConfigLoader"]

logger = logging.getLogger(__name__)

_CONFIG_PATH = ".github/ai-gate.yml"


class GitHubConfigLoader(IConfigLoader):
    """Loads and validates per-repo configuration via the GitHub API.

    Falls back to sensible defaults when the file is missing or contains
    invalid YAML.
    """

    def __init__(self, github_client: IGitHubClient) -> None:
        self._client = github_client

    async def load(self, owner: str, repo: str) -> AppConfig:
        """Load configuration for *owner/repo*.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            A validated :class:`AppConfig` instance.
        """
        content = await self._client.get_file_content(owner, repo, _CONFIG_PATH)

        if content is None:
            logger.debug("No config file found for %s/%s — using defaults", owner, repo)
            return AppConfig()

        try:
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                logger.warning("Config for %s/%s is not a mapping — using defaults", owner, repo)
                return AppConfig()
            return AppConfig(**data)
        except yaml.YAMLError as exc:
            logger.warning("Invalid YAML in config for %s/%s: %s — using defaults", owner, repo, exc)
            return AppConfig()
        except ValidationError as exc:
            logger.warning("Invalid config for %s/%s: %s — using defaults", owner, repo, exc)
            return AppConfig()
