"""Action dispatcher — decides and executes actions based on analysis results.

Every pull-request dispatch always tries to post a GitHub Check Run first so a
``success`` / ``neutral`` / ``failure`` status appears on the PR regardless of
which optional actions (labels, comment, close, request-changes) fire.  Each
optional action is wrapped in its own logged try/except so a single GitHub-API
failure (rate-limit, transient 5xx, permission gap) cannot silently terminate
the rest of the dispatch chain.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from src.application.comment_builder import CommentBuilder
from src.domain.entities import AnalysisResult, ContributionContext
from src.domain.enums import ContributionType
from src.domain.interfaces import IGitHubClient
from src.infrastructure.config.schema import AppConfig

__all__ = ["ActionDispatcher"]

logger = logging.getLogger(__name__)

# Conclusions are the strings the GitHub Checks API accepts; see
# https://docs.github.com/en/rest/checks/runs#create-a-check-run
_CONCLUSION_SUCCESS = "success"
_CONCLUSION_NEUTRAL = "neutral"
_CONCLUSION_FAILURE = "failure"


class ActionDispatcher:
    """Decides which actions to take and executes them via the GitHub client.

    The dispatch always begins by posting a check run for pull requests so the
    Checks tab and any branch-protection rule sees a definitive verdict.  After
    that, depending on the analysis result and repository configuration, the
    dispatcher applies labels, posts a comment, and optionally requests changes
    or closes the contribution.
    """

    def __init__(self, github_client: IGitHubClient) -> None:
        self._client = github_client
        self._comment_builder = CommentBuilder()

    async def dispatch(
        self,
        context: ContributionContext,
        result: AnalysisResult,
        config: AppConfig,
    ) -> None:
        """Execute every visible action for a completed analysis.

        Args:
            context: The contribution being analysed.
            result: The completed analysis result.
            config: The repository's configuration.
        """
        # The check run is the primary visible artefact for PRs — post it first
        # so it lands even if any subsequent label/comment call fails.
        await self._post_check_run_safely(context, result, config)

        try:
            await self._apply_optional_actions(context, result, config)
        except Exception as exc:  # top-level safety net — fence the whole optional-action chain
            logger.exception(
                "dispatch: optional-action chain failed for %s/%s#%d: %s",
                context.repo_owner,
                context.repo_name,
                context.number,
                exc,
            )

    # ------------------------------------------------------------------ #
    # Check run
    # ------------------------------------------------------------------ #

    async def _post_check_run_safely(
        self,
        context: ContributionContext,
        result: AnalysisResult,
        config: AppConfig,
    ) -> None:
        """Post a Check Run for the PR's head commit, swallowing API errors.

        Issues do not have a commit to attach a check run to, so this is a
        no-op for them.  Failures here are logged but never raised so the rest
        of the dispatch chain can still execute.
        """
        if context.contribution_type != ContributionType.PULL_REQUEST:
            return
        if not context.head_sha:
            logger.warning(
                "dispatch: PR %s/%s#%d has no head_sha — skipping check run",
                context.repo_owner,
                context.repo_name,
                context.number,
            )
            return

        conclusion, title, summary, details = self._build_check_run_payload(result, config)

        try:
            await self._client.create_check_run(
                context.repo_owner,
                context.repo_name,
                context.head_sha,
                title,
                summary,
                conclusion,
                details,
            )
        except Exception as exc:  # check-run failures must never abort the dispatch chain
            logger.exception(
                "dispatch: create_check_run failed for %s/%s@%s: %s",
                context.repo_owner,
                context.repo_name,
                context.head_sha[:8] if context.head_sha else "?",
                exc,
            )

    def _build_check_run_payload(
        self,
        result: AnalysisResult,
        config: AppConfig,
    ) -> tuple[str, str, str, str]:
        """Compute the (conclusion, title, summary, details) tuple for a PR.

        The conclusion follows this precedence:

        - ``failure`` — AI score >= ai.fail OR quality score < quality.minimum
        - ``neutral`` — AI score >= ai.warn (suspicious but below the fail bar)
        - ``success`` — everything else
        """
        ai_score = result.ai_score
        q_score = result.quality_report.score
        grade = result.quality_report.grade.value
        confidence = result.ai_confidence.value

        ai_fails = ai_score >= config.ai.fail
        ai_warns = ai_score >= config.ai.warn
        quality_fails = q_score < config.quality.minimum

        if ai_fails or quality_fails:
            conclusion = _CONCLUSION_FAILURE
        elif ai_warns:
            conclusion = _CONCLUSION_NEUTRAL
        else:
            conclusion = _CONCLUSION_SUCCESS

        title = f"AI {ai_score}/100 · Quality {q_score}/100 (grade {grade})"
        summary = self._build_summary(conclusion, ai_score, q_score, grade, confidence)
        details = self._build_details(result, config)
        return conclusion, title, summary, details

    @staticmethod
    def _build_summary(
        conclusion: str,
        ai_score: int,
        q_score: int,
        grade: str,
        confidence: str,
    ) -> str:
        """One-line GitHub Checks UI summary."""
        scores = (
            f"- AI detection: **{ai_score}/100** ({confidence} confidence)\n"
            f"- Quality: **{q_score}/100** (grade {grade})"
        )
        match conclusion:
            case "failure":
                return (
                    "AI Quality Gate flagged this pull request.\n\n"
                    + scores
                    + "\n\nSee the PR comment for the specific issues to address."
                )
            case "neutral":
                return (
                    "AI Quality Gate detected AI-content signals but the PR is otherwise acceptable.\n\n"
                    + scores
                )
            case _:
                return "AI Quality Gate passed this pull request.\n\n" + scores

    @staticmethod
    def _build_details(result: AnalysisResult, config: AppConfig) -> str:
        """Expanded markdown shown in the Checks tab body."""
        lines: list[str] = [
            "### Scores",
            "",
            f"- **AI detection**: {result.ai_score}/100 ({result.ai_confidence.value} confidence)",
            f"  - Warn threshold: {config.ai.warn}",
            f"  - Fail threshold: {config.ai.fail}",
            f"- **Quality**: {result.quality_report.score}/100 (grade {result.quality_report.grade.value})",
            f"  - Minimum threshold: {config.quality.minimum}",
        ]

        if result.ai_signals:
            lines.extend(["", "### Top AI signals", ""])
            for signal in result.ai_signals[:5]:
                count = f" (x{signal.occurrences})" if signal.occurrences > 1 else ""
                lines.append(f"- `{signal.pattern}`{count} — {signal.description}")

        failed = result.quality_report.failed_checks
        if failed:
            lines.extend(["", "### Failed quality checks", ""])
            for check in failed:
                lines.append(f"- **{check.name}**: {check.detail}")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Optional actions (labels, comment, close, request-changes)
    # ------------------------------------------------------------------ #

    async def _apply_optional_actions(
        self,
        context: ContributionContext,
        result: AnalysisResult,
        config: AppConfig,
    ) -> None:
        """Apply labels, comments, and decide on close/request-changes."""
        should_act_ai = result.ai_score >= config.ai.warn
        should_act_quality = result.quality_report.score < config.quality.minimum

        if not should_act_ai and not should_act_quality:
            # Still label high-quality contributions even when nothing is wrong.
            if result.quality_report.score >= 80:
                await self._safe_call(
                    "add_labels",
                    self._client.add_labels,
                    context.repo_owner,
                    context.repo_name,
                    context.number,
                    [config.labels.high_quality],
                )
            return

        labels = self._determine_labels(result, config)
        if labels:
            await self._safe_call(
                "add_labels",
                self._client.add_labels,
                context.repo_owner,
                context.repo_name,
                context.number,
                labels,
            )

        comment = self._comment_builder.build(context, result, config)
        if comment:
            await self._safe_call(
                "post_comment",
                self._client.post_comment,
                context.repo_owner,
                context.repo_name,
                context.number,
                comment,
            )

        action = self._determine_action(result, config)
        match action:
            case "close":
                await self._safe_call(
                    "close_contribution",
                    self._client.close_contribution,
                    context.repo_owner,
                    context.repo_name,
                    context.number,
                )
            case "request-changes" if context.contribution_type == ContributionType.PULL_REQUEST:
                if comment:
                    await self._safe_call(
                        "request_changes",
                        self._client.request_changes,
                        context.repo_owner,
                        context.repo_name,
                        context.number,
                        comment,
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

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    async def _safe_call(
        name: str,
        coro_fn: Callable[..., Awaitable[Any]],
        *args: Any,
    ) -> None:
        """Run a GitHub-client coroutine and log (don't propagate) any failure."""
        try:
            await coro_fn(*args)
        except Exception as exc:  # fence per-action failures so one 4xx doesn't kill the chain
            logger.exception("dispatch: %s failed: %s", name, exc)

    def _determine_labels(self, result: AnalysisResult, config: AppConfig) -> list[str]:
        """Select labels to apply based on analysis scores."""
        labels: list[str] = []

        if result.ai_score >= config.ai.fail:
            labels.append(config.labels.ai_detected)
        elif result.ai_score >= config.ai.warn:
            labels.append(config.labels.ai_warning)

        if result.quality_report.score < config.quality.minimum:
            labels.append(config.labels.low_quality)

        return labels

    def _determine_action(self, result: AnalysisResult, config: AppConfig) -> str:
        """Select the strongest action (close > request-changes > comment)."""
        actions: list[str] = []

        if result.ai_score >= config.ai.fail:
            actions.append(config.ai.action)
        if result.quality_report.score < config.quality.minimum:
            actions.append(config.quality.action)

        if "close" in actions:
            return "close"
        if "request-changes" in actions:
            return "request-changes"
        return "comment"
