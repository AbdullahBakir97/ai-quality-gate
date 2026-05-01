"""Comprehensive tests for the human, specific comment builder.

These tests verify three things at once:
  1. The comment is *correctly structured* (sections present/absent based on flags).
  2. The comment is *specific* (mentions the actual triggers, not generic text).
  3. The comment is *actionable* (every "missing X" has a concrete next step).
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from src.application.comment_builder import CommentBuilder
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
from src.infrastructure.config.schema import AppConfig

# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #


@pytest.fixture
def builder() -> CommentBuilder:
    return CommentBuilder()


@pytest.fixture
def config() -> AppConfig:
    return AppConfig()


def _ctx(
    *,
    contribution_type: ContributionType = ContributionType.ISSUE,
    title: str = "Sample title",
    body: str = "Sample body",
    number: int = 1,
) -> ContributionContext:
    return ContributionContext(
        title=title,
        body=body,
        author="test-user",
        labels=[],
        is_bot=False,
        contribution_type=contribution_type,
        number=number,
        repo_owner="testorg",
        repo_name="testrepo",
    )


def _ai_result(
    score: int,
    *,
    confidence: Confidence = Confidence.HIGH,
    signals: list[Signal] | None = None,
    quality_score: int = 100,
    quality_checks: list[QualityCheck] | None = None,
    contribution_type: ContributionType = ContributionType.ISSUE,
) -> AnalysisResult:
    # When the caller passes explicit checks, derive the report from them.
    # When the caller passes only a quality_score, fabricate a report at that
    # score with no failing checks (used for "AI flagged but quality fine" cases).
    if quality_checks is not None:
        quality_report = QualityReport.from_checks(quality_checks)
    elif quality_score == 100:
        quality_report = QualityReport.from_checks([QualityCheck("body-present", 15, 15, "Description provided")])
    else:
        quality_report = QualityReport(
            score=quality_score,
            grade=Grade.F if quality_score < 20 else Grade.C,
            checks=[],
        )

    return AnalysisResult(
        ai_score=score,
        ai_confidence=confidence,
        ai_signals=signals or [],
        is_likely_ai=score >= 50,
        quality_report=quality_report,
        contribution_type=contribution_type,
    )


# ------------------------------------------------------------------ #
# Scenario 1: Clean contribution — no flags, no comment
# ------------------------------------------------------------------ #


class TestNoFlags:
    """A clean human contribution with high quality should produce no comment."""

    def test_no_comment_when_nothing_flagged(self, builder, config):
        result = _ai_result(score=5, quality_score=85, confidence=Confidence.MINIMAL)
        ctx = _ctx(title="TypeError on empty email", body="Detailed reproduction steps below...")

        comment = builder.build(ctx, result, config)

        assert comment == ""


# ------------------------------------------------------------------ #
# Scenario 2: AI detected only — explain *which* signals and why
# ------------------------------------------------------------------ #


class TestAIOnlyFlag:
    """When AI is flagged but quality is fine, comment focuses on AI signals."""

    def test_comment_explains_specific_ai_signals(self, builder, config):
        signals = [
            Signal(SignalType.AI_VOCABULARY, "delve", "delve", weight=0.3),
            Signal(SignalType.AI_PHRASING, "I'd be happy to", "I'd be happy to", weight=0.4),
            Signal(SignalType.AI_PHRASING, "hope this helps", "hope this helps", weight=0.4),
        ]
        result = _ai_result(score=72, signals=signals, quality_score=85)
        ctx = _ctx()

        comment = builder.build(ctx, result, config)

        # Specific patterns must appear verbatim in the comment
        assert "`delve`" in comment
        assert "`I'd be happy to`" in comment
        assert "`hope this helps`" in comment

        # Specific human explanations, not just signal types
        assert "only appears in AI output" in comment
        assert "AI assistant opener" in comment

        # No quality section when quality is fine
        assert "What's Needed" not in comment

    def test_comment_severity_changes_at_fail_threshold(self, builder, config):
        signals = [Signal(SignalType.AI_PHRASING, "delve", "delve", weight=0.3)]

        warn_result = _ai_result(score=55, signals=signals, quality_score=85)
        fail_result = _ai_result(score=85, signals=signals, quality_score=85)
        ctx = _ctx()

        warn_comment = builder.build(ctx, warn_result, config)
        fail_comment = builder.build(ctx, fail_result, config)

        # Warn-level message is gentler
        assert "may be AI-assisted" in warn_comment or "patterns commonly found" in warn_comment

        # Fail-level message is more definitive
        assert "very likely AI-generated" in fail_comment

    def test_pull_request_uses_pull_request_subject(self, builder, config):
        result = _ai_result(
            score=85,
            signals=[Signal(SignalType.AI_PHRASING, "delve", "delve", weight=0.3)],
            quality_score=85,
            contribution_type=ContributionType.PULL_REQUEST,
        )
        ctx = _ctx(contribution_type=ContributionType.PULL_REQUEST)

        comment = builder.build(ctx, result, config)

        assert "pull request" in comment.lower()
        assert "issue" not in comment.lower().replace("issue/pr", "").replace("issue.", "pull")


# ------------------------------------------------------------------ #
# Scenario 3: Quality only — concrete advice per missing element
# ------------------------------------------------------------------ #


class TestQualityOnlyFlag:
    """When quality is flagged but AI is fine, focus on what's missing."""

    def test_advice_is_specific_per_missing_element(self, builder, config):
        # All checks fail to push the score below the quality threshold (30).
        checks = [
            QualityCheck("title-specificity", 0, 10, "Vague title"),
            QualityCheck("reproduction-steps", 0, 10, "No reproduction steps found"),
            QualityCheck("environment-info", 0, 5, "No environment info"),
            QualityCheck("body-present", 0, 15, "No description"),
        ]
        result = _ai_result(score=5, quality_checks=checks, confidence=Confidence.MINIMAL)
        ctx = _ctx(title="bug", body="")

        comment = builder.build(ctx, result, config)

        # The advice must cite the specific check by friendly name
        assert "Title Specificity" in comment
        assert "Reproduction Steps" in comment
        assert "Environment Info" in comment

        # The advice must include concrete examples — not just "add details"
        assert "TypeError in login form" in comment  # title example
        assert "Go to `/login`" in comment  # repro example
        assert "OS, browser" in comment  # env example

        # AI section should not appear
        assert "AI Content" not in comment

    def test_passing_checks_are_not_listed(self, builder, config):
        # Push score below threshold (30) — fail enough checks to dip under,
        # but keep at least one passing check we can assert is *omitted*.
        # 5 passing / 65 max = 8% which is well below the 30 threshold.
        checks = [
            QualityCheck("title-length", 5, 5, "Good"),  # passing — must NOT appear
            QualityCheck("reproduction-steps", 0, 15, "Missing"),  # failing — must appear
            QualityCheck("environment-info", 0, 15, "Missing"),  # failing
            QualityCheck("code-snippets", 0, 15, "Missing"),  # failing
            QualityCheck("search-evidence", 0, 15, "Missing"),  # failing
        ]
        result = _ai_result(score=5, quality_checks=checks, confidence=Confidence.MINIMAL)
        ctx = _ctx()

        comment = builder.build(ctx, result, config)

        # Failing checks listed
        assert "Reproduction Steps" in comment
        assert "Environment Info" in comment
        # Passing checks omitted
        assert "Title Length" not in comment
        assert "Body Length" not in comment

    def test_partial_check_labelled_partial_not_missing(self, builder, config):
        checks = [
            QualityCheck("body-length", 5, 10, "Could be more detailed"),
            QualityCheck("title-specificity", 0, 10, "Vague title"),
        ]
        result = _ai_result(score=5, quality_checks=checks, confidence=Confidence.MINIMAL)
        ctx = _ctx()

        comment = builder.build(ctx, result, config)

        assert "Partial — Body Length" in comment
        assert "Missing — Title Specificity" in comment


# ------------------------------------------------------------------ #
# Scenario 4: Both flagged — combined comment
# ------------------------------------------------------------------ #


class TestCombinedFlags:
    """When both AI and quality fire, the comment covers both with one header."""

    def test_combined_comment_contains_both_sections(self, builder, config):
        signals = [
            Signal(SignalType.AI_VOCABULARY, "delve", "delve", weight=0.3),
            Signal(SignalType.AI_PHRASING, "I'd be happy to", "I'd be happy to", weight=0.4),
        ]
        checks = [
            QualityCheck("reproduction-steps", 0, 10, "Missing"),
            QualityCheck("environment-info", 0, 5, "Missing"),
        ]
        result = _ai_result(score=78, signals=signals, quality_checks=checks)
        ctx = _ctx(title="bug", body="ai-generated description with delve phrases")

        comment = builder.build(ctx, result, config)

        # Both sections appear
        assert "AI Content" in comment
        assert "What's Needed" in comment

        # Single header with both rows
        assert "AI Detection |" in comment
        assert "Quality |" in comment

        # Sections separated by horizontal rule
        assert "---" in comment


# ------------------------------------------------------------------ #
# Scenario 5: Empty issue (the spammer case)
# ------------------------------------------------------------------ #


class TestEmptyIssue:
    """The classic empty 'bug' / 'help' issue."""

    def test_empty_issue_gets_focused_advice(self, builder, config):
        checks = [
            QualityCheck("title-specificity", 0, 10, "Vague title"),
            QualityCheck("body-present", 0, 15, "No description provided"),
            QualityCheck("reproduction-steps", 0, 10, "No reproduction steps"),
        ]
        result = _ai_result(score=5, quality_checks=checks, confidence=Confidence.MINIMAL)
        ctx = _ctx(title="bug", body="")

        comment = builder.build(ctx, result, config)

        assert "Body Present" in comment
        assert "what is the problem" in comment
        assert "what have you tried" in comment


# ------------------------------------------------------------------ #
# Scenario 6: PR-specific advice
# ------------------------------------------------------------------ #


class TestPullRequestAdvice:
    """PR-specific quality checks should produce PR-specific advice."""

    def test_missing_linked_issue_advice_is_pr_specific(self, builder, config):
        checks = [QualityCheck("linked-issue", 0, 10, "No linked issue")]
        result = _ai_result(
            score=5,
            quality_checks=checks,
            confidence=Confidence.MINIMAL,
            contribution_type=ContributionType.PULL_REQUEST,
        )
        ctx = _ctx(contribution_type=ContributionType.PULL_REQUEST)

        comment = builder.build(ctx, result, config)

        assert "Closes #N" in comment or "Fixes #N" in comment
        assert "auto-closes" in comment.lower() or "auto-close" in comment.lower()

    def test_missing_tests_advice_is_actionable(self, builder, config):
        checks = [QualityCheck("tests-included", 0, 10, "No test files in diff")]
        result = _ai_result(
            score=5,
            quality_checks=checks,
            confidence=Confidence.MINIMAL,
            contribution_type=ContributionType.PULL_REQUEST,
        )
        ctx = _ctx(contribution_type=ContributionType.PULL_REQUEST)

        comment = builder.build(ctx, result, config)

        assert "test changes" in comment.lower() or "test file" in comment.lower()
        assert "existing tests" in comment.lower()  # offers an out for "already covered"

    def test_missing_breaking_change_advice_mentions_migration(self, builder, config):
        checks = [QualityCheck("breaking-change", 0, 5, "Possible breaking change")]
        result = _ai_result(
            score=5,
            quality_checks=checks,
            confidence=Confidence.MINIMAL,
            contribution_type=ContributionType.PULL_REQUEST,
        )
        ctx = _ctx(contribution_type=ContributionType.PULL_REQUEST)

        comment = builder.build(ctx, result, config)

        assert "BREAKING CHANGE" in comment
        assert "migrate" in comment.lower()


# ------------------------------------------------------------------ #
# Scenario 7: No human-text in the bot — never reads as a robot
# ------------------------------------------------------------------ #


class TestVoiceQuality:
    """The comment should not contain phrases AI Quality Gate itself flags as bot-y."""

    AI_TRIGGERS: ClassVar[list[str]] = [
        "I'd be happy to",
        "hope this helps",
        "feel free to reach out",
        "let me know if you",
        "here's a breakdown",
    ]

    def test_comment_does_not_use_ai_phrases(self, builder, config):
        signals = [Signal(SignalType.AI_PHRASING, "delve", "delve", weight=0.3)]
        checks = [QualityCheck("reproduction-steps", 0, 10, "Missing")]
        result = _ai_result(score=78, signals=signals, quality_checks=checks)
        ctx = _ctx()

        comment = builder.build(ctx, result, config)

        for phrase in self.AI_TRIGGERS:
            # The phrase 'I\'d be happy to' may legitimately appear inside the
            # signal-explanation backticks and quoted examples; we check only
            # the prose around them.
            #
            # Strategy: count occurrences outside of backticks.
            non_code_text = "\n".join(
                line for line in comment.split("\n") if not line.lstrip().startswith("- `")
            ).lower()
            assert phrase.lower() not in non_code_text, f"Comment contains AI-style phrase '{phrase}' in prose"

    def test_comment_uses_imperative_action_verbs(self, builder, config):
        """Actionable advice should start with verbs like 'Add', 'Include', 'Use'."""
        # Use a wider mix of failing checks so the comment exercises multiple
        # advice templates — each template is expected to use a distinct verb.
        checks = [
            QualityCheck("reproduction-steps", 0, 10, "Missing"),
            QualityCheck("code-snippets", 0, 10, "Missing"),
            QualityCheck("search-evidence", 0, 5, "Missing"),
            QualityCheck("linked-issue", 0, 10, "Missing"),
        ]
        result = _ai_result(score=5, quality_checks=checks, confidence=Confidence.MINIMAL)
        ctx = _ctx()

        comment = builder.build(ctx, result, config)

        # At least two of these imperative verbs appear in the advice prose.
        imperatives = ["Add", "Include", "Use", "Paste", "Describe", "Link", "Attach", "Have"]
        found = [v for v in imperatives if v in comment]
        assert len(found) >= 2, f"Comment lacks imperative action verbs. Found only: {found}\n\n{comment}"


# ------------------------------------------------------------------ #
# Scenario 8: Score bars and footer
# ------------------------------------------------------------------ #


class TestVisualSignals:
    """The score bars should communicate severity at a glance."""

    def test_high_ai_score_shows_red_indicator(self, builder, config):
        signals = [Signal(SignalType.AI_PHRASING, "delve", "delve", weight=0.3)]
        result = _ai_result(score=85, signals=signals, quality_score=85)
        ctx = _ctx()

        comment = builder.build(ctx, result, config)

        # Red indicator for high AI score
        assert "🔴" in comment

    def test_low_quality_score_shows_red_indicator(self, builder, config):
        checks = [QualityCheck("body-present", 0, 15, "Missing")]
        result = _ai_result(score=5, quality_checks=checks, confidence=Confidence.MINIMAL)
        ctx = _ctx()

        comment = builder.build(ctx, result, config)

        assert "🔴" in comment

    def test_footer_links_to_project(self, builder, config):
        signals = [Signal(SignalType.AI_PHRASING, "delve", "delve", weight=0.3)]
        result = _ai_result(score=85, signals=signals, quality_score=85)
        ctx = _ctx()

        comment = builder.build(ctx, result, config)

        assert "github.com/AbdullahBakir97/ai-quality-gate" in comment
