"""Tests for ActionDispatcher.

The dispatcher is the *visible-output* layer of the bot — these tests verify
the most important guarantees:

1. **Every PR dispatch posts a check run.**  This is the single signal that
   appears in GitHub's Checks tab and branch-protection settings; the bot is
   effectively invisible without it.
2. **Conclusion follows the configured thresholds.**  success / neutral /
   failure must line up with ai.warn, ai.fail, and quality.minimum.
3. **Issues do not attempt a check run.**  They have no commit to attach to.
4. **A failing label call does not silence the rest of the dispatch.**
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.application.action_dispatcher import ActionDispatcher
from src.domain.entities import (
    AnalysisResult,
    ContributionContext,
    QualityCheck,
    QualityReport,
    Signal,
)
from src.domain.enums import (
    Confidence,
    ContributionType,
    Grade,
    SignalType,
)
from src.domain.interfaces import IGitHubClient
from src.infrastructure.config.schema import AppConfig

# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #


@pytest.fixture
def fake_client() -> AsyncMock:
    """An IGitHubClient mock that records every call."""
    client = AsyncMock(spec=IGitHubClient)
    return client


@pytest.fixture
def dispatcher(fake_client: AsyncMock) -> ActionDispatcher:
    return ActionDispatcher(fake_client)


@pytest.fixture
def config() -> AppConfig:
    return AppConfig()


def _quality_report(score: int) -> QualityReport:
    """Build a QualityReport with the given normalized score.

    Uses one weighted check so the report's ``score`` matches ``score``
    exactly without needing to compute through ``from_checks``.
    """
    grade = (
        Grade.A if score >= 90
        else Grade.B if score >= 80
        else Grade.C if score >= 70
        else Grade.D if score >= 60
        else Grade.F
    )
    return QualityReport(
        score=score,
        grade=grade,
        checks=[QualityCheck(name="overall", score=score, max_score=100, detail="")],
    )


def _result(
    *,
    ai_score: int,
    quality_score: int,
    confidence: Confidence = Confidence.LOW,
    contribution_type: ContributionType = ContributionType.PULL_REQUEST,
    signals: list[Signal] | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        ai_score=ai_score,
        ai_confidence=confidence,
        ai_signals=signals or [],
        is_likely_ai=ai_score >= 50,
        quality_report=_quality_report(quality_score),
        contribution_type=contribution_type,
    )


def _check_run_call_kwargs(client: AsyncMock) -> dict[str, Any] | None:
    """Return the positional args of the last create_check_run call as a dict."""
    if not client.create_check_run.await_args_list:
        return None
    args = client.create_check_run.await_args_list[-1].args
    # Signature: (owner, repo, head_sha, title, summary, conclusion, details)
    keys = ("owner", "repo", "head_sha", "title", "summary", "conclusion", "details")
    return dict(zip(keys, args, strict=False))


# ------------------------------------------------------------------ #
# Check run is always created for PR dispatches
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_clean_pr_posts_success_check_run(
    dispatcher: ActionDispatcher,
    fake_client: AsyncMock,
    pr_context: ContributionContext,
    config: AppConfig,
) -> None:
    """A PR below all thresholds gets a `success` check run."""
    result = _result(ai_score=10, quality_score=85)

    await dispatcher.dispatch(pr_context, result, config)

    call = _check_run_call_kwargs(fake_client)
    assert call is not None, "create_check_run must be called for PR dispatches"
    assert call["conclusion"] == "success"
    assert call["owner"] == pr_context.repo_owner
    assert call["repo"] == pr_context.repo_name
    assert call["head_sha"] == pr_context.head_sha
    assert "85/100" in call["summary"]
    assert "10/100" in call["summary"]


@pytest.mark.asyncio
async def test_ai_warn_only_pr_posts_neutral_check_run(
    dispatcher: ActionDispatcher,
    fake_client: AsyncMock,
    pr_context: ContributionContext,
    config: AppConfig,
) -> None:
    """Above ai.warn but below ai.fail and quality OK → `neutral`."""
    # default config: ai.warn=50, ai.fail=80, quality.minimum=30
    result = _result(ai_score=60, quality_score=70)

    await dispatcher.dispatch(pr_context, result, config)

    call = _check_run_call_kwargs(fake_client)
    assert call is not None
    assert call["conclusion"] == "neutral"


@pytest.mark.asyncio
async def test_ai_fail_pr_posts_failure_check_run(
    dispatcher: ActionDispatcher,
    fake_client: AsyncMock,
    pr_context: ContributionContext,
    config: AppConfig,
) -> None:
    """Above ai.fail → `failure` regardless of quality."""
    result = _result(ai_score=90, quality_score=80)

    await dispatcher.dispatch(pr_context, result, config)

    call = _check_run_call_kwargs(fake_client)
    assert call is not None
    assert call["conclusion"] == "failure"


@pytest.mark.asyncio
async def test_low_quality_pr_posts_failure_check_run(
    dispatcher: ActionDispatcher,
    fake_client: AsyncMock,
    pr_context: ContributionContext,
    config: AppConfig,
) -> None:
    """Below quality.minimum → `failure` even if AI is clean."""
    result = _result(ai_score=10, quality_score=20)  # default minimum is 30

    await dispatcher.dispatch(pr_context, result, config)

    call = _check_run_call_kwargs(fake_client)
    assert call is not None
    assert call["conclusion"] == "failure"


# ------------------------------------------------------------------ #
# Issues do not produce check runs
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_issue_dispatch_does_not_post_check_run(
    dispatcher: ActionDispatcher,
    fake_client: AsyncMock,
    issue_context: ContributionContext,
    config: AppConfig,
) -> None:
    """Issues have no commit to attach a check run to — must be a no-op."""
    result = _result(
        ai_score=10,
        quality_score=85,
        contribution_type=ContributionType.ISSUE,
    )

    await dispatcher.dispatch(issue_context, result, config)

    fake_client.create_check_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_pr_without_head_sha_does_not_post_check_run(
    dispatcher: ActionDispatcher,
    fake_client: AsyncMock,
    pr_context: ContributionContext,
    config: AppConfig,
) -> None:
    """Defensive: a PR payload that omits head.sha must not raise."""
    pr_context.head_sha = None
    result = _result(ai_score=10, quality_score=85)

    await dispatcher.dispatch(pr_context, result, config)

    fake_client.create_check_run.assert_not_awaited()


# ------------------------------------------------------------------ #
# Resilience — one API failure doesn't kill the chain
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_label_failure_does_not_block_check_run(
    dispatcher: ActionDispatcher,
    fake_client: AsyncMock,
    pr_context: ContributionContext,
    config: AppConfig,
) -> None:
    """add_labels raising must not prevent the check run from being posted."""
    fake_client.add_labels.side_effect = RuntimeError("simulated GitHub 422")
    # High quality PR — would normally only add a label
    result = _result(ai_score=10, quality_score=90)

    await dispatcher.dispatch(pr_context, result, config)

    # Check run still posted
    fake_client.create_check_run.assert_awaited()


@pytest.mark.asyncio
async def test_check_run_failure_does_not_block_comment(
    dispatcher: ActionDispatcher,
    fake_client: AsyncMock,
    pr_context: ContributionContext,
    config: AppConfig,
) -> None:
    """create_check_run raising must not prevent comment/label posting."""
    fake_client.create_check_run.side_effect = RuntimeError("simulated 5xx")
    # Low quality PR — would normally post a comment + labels
    result = _result(ai_score=10, quality_score=10)

    await dispatcher.dispatch(pr_context, result, config)

    # Comment + labels still attempted
    fake_client.add_labels.assert_awaited()
    fake_client.post_comment.assert_awaited()


# ------------------------------------------------------------------ #
# Check run payload shape
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_check_run_payload_includes_signals_and_failed_checks(
    dispatcher: ActionDispatcher,
    fake_client: AsyncMock,
    pr_context: ContributionContext,
    config: AppConfig,
) -> None:
    """Details body should surface top AI signals and failed quality checks."""
    signals = [
        Signal(
            type=SignalType.AI_VOCABULARY,
            pattern="delve",
            description="AI-typical vocabulary",
            weight=10,
            occurrences=3,
        )
    ]
    result = AnalysisResult(
        ai_score=85,
        ai_confidence=Confidence.HIGH,
        ai_signals=signals,
        is_likely_ai=True,
        quality_report=QualityReport(
            score=20,
            grade=Grade.F,
            checks=[
                QualityCheck(
                    name="body-present",
                    score=0,
                    max_score=10,
                    detail="No body provided",
                )
            ],
        ),
        contribution_type=ContributionType.PULL_REQUEST,
    )

    await dispatcher.dispatch(pr_context, result, config)

    call = _check_run_call_kwargs(fake_client)
    assert call is not None
    assert "delve" in call["details"]
    assert "body-present" in call["details"]
    assert call["conclusion"] == "failure"
