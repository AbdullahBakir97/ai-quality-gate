"""Dependency injection container — wires all layers together."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.analyzers.detectors import (
    CodeDetector,
    HallucinationDetector,
    PatternDetector,
    StructureDetector,
)
from src.analyzers.patterns import PatternRegistry, register_default_patterns
from src.application.action_dispatcher import ActionDispatcher
from src.application.orchestrator import AnalysisOrchestrator
from src.application.webhook_handler import WebhookHandler
from src.infrastructure.config.loader import GitHubConfigLoader
from src.infrastructure.github.auth import GitHubAuthenticator
from src.infrastructure.github.client import GitHubClient
from src.infrastructure.github.webhook import WebhookVerifier

if TYPE_CHECKING:
    from src.config.settings import Settings

__all__ = ["Container"]


class Container:
    """Composes all application dependencies into a single object graph.

    Instantiated once at startup and stored on ``app.state.container``
    so that FastAPI dependency-injection helpers can retrieve individual
    components.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # --- Infrastructure ---
        self.github_auth = GitHubAuthenticator(
            settings.app_id,
            settings.get_private_key(),
        )
        self.github_client = GitHubClient(self.github_auth)
        self.webhook_verifier: WebhookVerifier | None = (
            WebhookVerifier(settings.webhook_secret) if settings.webhook_secret else None
        )
        self.config_loader = GitHubConfigLoader(self.github_client)

        # --- Analyzers ---
        self.pattern_registry = PatternRegistry()
        register_default_patterns(self.pattern_registry)

        self.detectors = [
            PatternDetector(self.pattern_registry),
            StructureDetector(self.pattern_registry),
            HallucinationDetector(self.pattern_registry),
            CodeDetector(self.pattern_registry),
        ]

        # Scorers and aggregator are imported lazily to allow the
        # analyzers package to be built incrementally.
        from src.analyzers.scorers import IssueScorer, PRScorer
        from src.analyzers.aggregator import SignalAggregator

        self.issue_scorer = IssueScorer()
        self.pr_scorer = PRScorer()
        self.aggregator = SignalAggregator()

        # --- Application ---
        self.orchestrator = AnalysisOrchestrator(
            self.detectors,
            self.issue_scorer,
            self.pr_scorer,
            self.aggregator,
        )
        self.action_dispatcher = ActionDispatcher(self.github_client)
        self.webhook_handler = WebhookHandler(
            self.orchestrator,
            self.action_dispatcher,
            self.config_loader,
        )
