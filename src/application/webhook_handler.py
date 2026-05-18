"""Webhook event handler — routes GitHub events to the analysis pipeline."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.domain.entities import ContributionContext
from src.domain.enums import ContributionType

if TYPE_CHECKING:
    from src.application.action_dispatcher import ActionDispatcher
    from src.application.orchestrator import AnalysisOrchestrator
    from src.domain.interfaces import IConfigLoader
    from src.infrastructure.config.schema import AppConfig

__all__ = ["WebhookHandler"]

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Routes incoming GitHub webhook events to the analysis pipeline.

    Handles ``issues`` and ``pull_request`` events, loads per-repo
    configuration, checks exemptions, and delegates to the orchestrator
    and action dispatcher.
    """

    def __init__(
        self,
        orchestrator: AnalysisOrchestrator,
        action_dispatcher: ActionDispatcher,
        config_loader: IConfigLoader,
    ) -> None:
        self._orchestrator = orchestrator
        self._action_dispatcher = action_dispatcher
        self._config_loader = config_loader

    # GitHub webhook actions we react to.  ``reopened`` is included so that
    # closing and re-opening a PR (a common manual re-trigger and a CI pattern
    # for verifying bot behaviour) re-runs the analysis.
    _PR_ACTIONS = ("opened", "edited", "reopened", "synchronize", "ready_for_review")
    _ISSUE_ACTIONS = ("opened", "edited", "reopened")

    async def handle_event(self, event_type: str, payload: dict) -> None:
        """Dispatch a webhook event for processing.

        Args:
            event_type: The GitHub event type (e.g. ``issues``, ``pull_request``).
            payload: The parsed JSON payload.
        """
        action = payload.get("action")
        match event_type:
            case "issues":
                if action in self._ISSUE_ACTIONS:
                    await self._handle_issue(payload)
                else:
                    logger.debug("Ignoring issues action: %s", action)
            case "pull_request":
                if action in self._PR_ACTIONS:
                    await self._handle_pull_request(payload)
                else:
                    logger.debug("Ignoring pull_request action: %s", action)
            case _:
                logger.debug("Ignoring event type: %s", event_type)

    async def _handle_issue(self, payload: dict) -> None:
        """Process an issue event."""
        repo = payload["repository"]
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        issue = payload["issue"]

        config = await self._config_loader.load(owner, repo_name)
        if not config.enabled or not config.analyze.issues:
            return

        user = issue["user"]
        labels = [lbl["name"] for lbl in issue.get("labels", [])]
        is_bot = user.get("type", "User") == "Bot"

        if self._is_exempt(config, user["login"], labels, is_bot):
            logger.info("User %s is exempt for %s/%s#%d", user["login"], owner, repo_name, issue["number"])
            return

        context = self._build_context(
            title=issue["title"],
            body=issue.get("body") or "",
            author=user["login"],
            labels=labels,
            is_bot=is_bot,
            contribution_type=ContributionType.ISSUE,
            number=issue["number"],
            repo_owner=owner,
            repo_name=repo_name,
        )

        result = await self._orchestrator.analyze(context)
        await self._action_dispatcher.dispatch(context, result, config)

    async def _handle_pull_request(self, payload: dict) -> None:
        """Process a pull-request event."""
        repo = payload["repository"]
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        pr = payload["pull_request"]

        config = await self._config_loader.load(owner, repo_name)
        if not config.enabled or not config.analyze.pull_requests:
            return

        user = pr["user"]
        labels = [lbl["name"] for lbl in pr.get("labels", [])]
        is_bot = user.get("type", "User") == "Bot"

        if self._is_exempt(config, user["login"], labels, is_bot):
            logger.info("User %s is exempt for %s/%s#%d", user["login"], owner, repo_name, pr["number"])
            return

        head_sha = pr.get("head", {}).get("sha")

        context = self._build_context(
            title=pr["title"],
            body=pr.get("body") or "",
            author=user["login"],
            labels=labels,
            is_bot=is_bot,
            contribution_type=ContributionType.PULL_REQUEST,
            number=pr["number"],
            repo_owner=owner,
            repo_name=repo_name,
            head_sha=head_sha,
        )

        result = await self._orchestrator.analyze(context)
        await self._action_dispatcher.dispatch(context, result, config)

    def _is_exempt(self, config: AppConfig, user: str, labels: list[str], is_bot: bool) -> bool:
        """Determine whether the contribution should be skipped.

        Args:
            config: The repository configuration.
            user: The author's login.
            labels: Labels currently on the issue/PR.
            is_bot: Whether the author is a bot account.

        Returns:
            ``True`` if the contribution is exempt from analysis.
        """
        if config.exempt.bots and is_bot:
            return True
        if user in config.exempt.users:
            return True
        return any(lbl in config.exempt.labels for lbl in labels)

    def _build_context(
        self,
        *,
        title: str,
        body: str,
        author: str,
        labels: list[str],
        is_bot: bool,
        contribution_type: ContributionType,
        number: int,
        repo_owner: str,
        repo_name: str,
        diff: str | None = None,
        head_sha: str | None = None,
    ) -> ContributionContext:
        """Construct a :class:`ContributionContext` from raw payload data."""
        return ContributionContext(
            title=title,
            body=body,
            author=author,
            labels=labels,
            is_bot=is_bot,
            contribution_type=contribution_type,
            number=number,
            repo_owner=repo_owner,
            repo_name=repo_name,
            diff=diff,
            head_sha=head_sha,
        )
