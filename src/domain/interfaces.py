"""Abstract interfaces (ports) for the AI Quality Gate domain."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import AnalysisResult, ContributionContext, QualityReport, Signal

__all__ = [
    "IDetector",
    "IScorer",
    "IGitHubClient",
    "IConfigLoader",
    "IActionHandler",
]


class IDetector(ABC):
    """Detects AI-generated content signals in text."""

    @abstractmethod
    async def detect(
        self, text: str, *, diff: str | None = None
    ) -> list[Signal]:
        ...


class IScorer(ABC):
    """Scores contribution quality against defined criteria."""

    @abstractmethod
    async def score(self, context: ContributionContext) -> QualityReport:
        ...


class IGitHubClient(ABC):
    """Abstraction over GitHub API operations."""

    @abstractmethod
    async def post_comment(
        self, owner: str, repo: str, number: int, body: str
    ) -> None:
        ...

    @abstractmethod
    async def add_labels(
        self, owner: str, repo: str, number: int, labels: list[str]
    ) -> None:
        ...

    @abstractmethod
    async def create_check_run(
        self,
        owner: str,
        repo: str,
        head_sha: str,
        title: str,
        summary: str,
        conclusion: str,
        details: str,
    ) -> None:
        ...

    @abstractmethod
    async def request_changes(
        self, owner: str, repo: str, number: int, body: str
    ) -> None:
        ...

    @abstractmethod
    async def close_contribution(
        self, owner: str, repo: str, number: int
    ) -> None:
        ...

    @abstractmethod
    async def get_file_content(
        self, owner: str, repo: str, path: str
    ) -> str | None:
        ...


class IConfigLoader(ABC):
    """Loads application configuration for a given repository."""

    @abstractmethod
    async def load(self, owner: str, repo: str) -> "AppConfig":
        ...


class IActionHandler(ABC):
    """Executes actions based on analysis results and configuration."""

    @abstractmethod
    async def handle(
        self,
        context: ContributionContext,
        result: AnalysisResult,
        config: "AppConfig",
    ) -> None:
        ...
