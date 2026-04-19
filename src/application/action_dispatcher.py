"""Action dispatcher — decides and executes actions based on analysis results."""

from __future__ import annotations

import logging

from src.domain.entities import AnalysisResult, ContributionContext
from src.domain.enums import ContributionType
from src.domain.interfaces import IGitHubClient
from src.infrastructure.config.defaults import MESSAGE_TEMPLATES
from src.infrastructure.config.schema import AppConfig

__all__ = ["ActionDispatcher"]

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """Decides which actions to take and executes them via the GitHub client.

    Based on the analysis result and repository configuration, the
    dispatcher applies labels, posts comments, and optionally requests
    changes or closes the contribution.
    """

    def __init__(self, github_client: IGitHubClient) -> None:
        self._client = github_client

    async def dispatch(
        self,
        context: ContributionContext,
        result: AnalysisResult,
        config: AppConfig,
    ) -> None:
        """Evaluate the analysis result and execute appropriate actions.

        Args:
            context: The contribution being analysed.
            result: The completed analysis result.
            config: The repository's configuration.
        """
        should_act_ai = result.ai_score >= config.ai.warn
        should_act_quality = result.quality_report.score < config.quality.minimum

        if not should_act_ai and not should_act_quality:
            # Still label high-quality contributions
            if result.quality_report.score >= 80:
                await self._client.add_labels(
                    context.repo_owner,
                    context.repo_name,
                    context.number,
                    [config.labels.high_quality],
                )
            return

        # Apply labels
        labels = self._determine_labels(result, config)
        if labels:
            await self._client.add_labels(
                context.repo_owner, context.repo_name, context.number, labels
            )

        # Build and post comment
        comment = self._build_comment(result, config)
        await self._client.post_comment(
            context.repo_owner, context.repo_name, context.number, comment
        )

        # Determine strongest action
        action = self._determine_action(result, config)
        match action:
            case "close":
                await self._client.close_contribution(
                    context.repo_owner, context.repo_name, context.number
                )
            case "request-changes" if context.contribution_type == ContributionType.PULL_REQUEST:
                await self._client.request_changes(
                    context.repo_owner, context.repo_name, context.number, comment
                )

        logger.info(
            "Dispatched action=%s for %s/%s#%d (ai=%d, quality=%d)",
            action,
            context.repo_owner,
            context.repo_name,
            context.number,
            result.ai_score,
            result.quality_report.score,
        )

    def _determine_labels(self, result: AnalysisResult, config: AppConfig) -> list[str]:
        """Select labels to apply based on analysis scores.

        Args:
            result: The analysis result.
            config: The repository configuration.

        Returns:
            A list of label names to apply.
        """
        labels: list[str] = []

        if result.ai_score >= config.ai.fail:
            labels.append(config.labels.ai_detected)
        elif result.ai_score >= config.ai.warn:
            labels.append(config.labels.ai_warning)

        if result.quality_report.score < config.quality.minimum:
            labels.append(config.labels.low_quality)

        return labels

    def _build_comment(self, result: AnalysisResult, config: AppConfig) -> str:
        """Build a markdown comment summarising the analysis.

        Args:
            result: The analysis result.
            config: The repository configuration.

        Returns:
            A formatted markdown string.
        """
        should_act_ai = result.ai_score >= config.ai.warn
        should_act_quality = result.quality_report.score < config.quality.minimum

        signals_text = "\n".join(
            f"- **{s.pattern}** — {s.description} (weight: {s.contribution:.1f})"
            for s in result.ai_signals[:10]
        ) or "_No signals detected._"

        improvements_text = "\n".join(
            f"- **{c.name}**: {c.detail} ({c.score}/{c.max_score})"
            for c in result.quality_report.failed_checks + result.quality_report.partial_checks
        ) or "_No improvements needed._"

        if should_act_ai and should_act_quality:
            template = MESSAGE_TEMPLATES["combined"]
        elif should_act_ai:
            template = MESSAGE_TEMPLATES["ai_warning"]
        else:
            template = MESSAGE_TEMPLATES["low_quality"]

        return template.format(
            ai_score=result.ai_score,
            confidence=result.ai_confidence.value,
            quality_score=result.quality_report.score,
            grade=result.quality_report.grade.value,
            signals=signals_text,
            improvements=improvements_text,
        )

    def _determine_action(self, result: AnalysisResult, config: AppConfig) -> str:
        """Select the strongest action to take.

        Args:
            result: The analysis result.
            config: The repository configuration.

        Returns:
            The action string (``comment``, ``request-changes``, or ``close``).
        """
        actions: list[str] = []

        if result.ai_score >= config.ai.fail:
            actions.append(config.ai.action)
        if result.quality_report.score < config.quality.minimum:
            actions.append(config.quality.action)

        # Priority: close > request-changes > comment
        if "close" in actions:
            return "close"
        if "request-changes" in actions:
            return "request-changes"
        return "comment"
