"""Tests for the issue quality scorer."""

import pytest

from src.analyzers.scorers.issue_scorer import IssueScorer
from src.domain.entities import ContributionContext


@pytest.fixture
def scorer() -> IssueScorer:
    return IssueScorer()


class TestIssueScorer:
    """Tests for issue quality scoring."""

    async def test_good_issue_scores_high(self, scorer: IssueScorer, issue_context: ContributionContext):
        report = await scorer.score(issue_context)
        assert report.score >= 60
        assert report.grade in ("A", "B")

    async def test_empty_issue_scores_low(self, scorer: IssueScorer, empty_issue_context: ContributionContext):
        report = await scorer.score(empty_issue_context)
        assert report.score < 20
        assert report.grade in ("D", "F")

    async def test_vague_title_penalized(self, scorer: IssueScorer):
        context = ContributionContext(
            title="bug",
            body="Something is broken and I don't know why. Please fix it.",
            author="user",
            labels=[],
            is_bot=False,
            contribution_type="issue",
            number=1,
            repo_owner="org",
            repo_name="repo",
        )
        report = await scorer.score(context)
        title_check = next((c for c in report.checks if "specificity" in c.name), None)
        assert title_check is not None
        assert title_check.score == 0

    async def test_code_snippets_rewarded(self, scorer: IssueScorer):
        context = ContributionContext(
            title="Error in parser module",
            body="When I run `parser.parse(data)` I get:\n```\nTypeError: unexpected None\n```",
            author="user",
            labels=[],
            is_bot=False,
            contribution_type="issue",
            number=1,
            repo_owner="org",
            repo_name="repo",
        )
        report = await scorer.score(context)
        code_check = next((c for c in report.checks if "code" in c.name), None)
        assert code_check is not None
        assert code_check.score > 0

    async def test_all_checks_have_valid_scores(self, scorer: IssueScorer, issue_context: ContributionContext):
        report = await scorer.score(issue_context)
        for check in report.checks:
            assert 0 <= check.score <= check.max_score
            assert check.name
            assert check.detail
