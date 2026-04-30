"""Pull request quality scorer -- evaluates PRs against quality criteria."""

import re

from src.domain.entities import ContributionContext, QualityCheck, QualityReport

from .base import BaseScorer

__all__ = ["PRScorer"]


class PRScorer(BaseScorer):
    """Scores pull requests on completeness, convention, and review-readiness."""

    async def score(self, context: ContributionContext) -> QualityReport:
        """Run all quality checks and return an aggregated report."""
        checks: list[QualityCheck] = [
            self._check_title_length(context.title),
            self._check_title_specificity(context.title),
            self._check_pr_title_convention(context.title),
            self._check_body_presence(context.body),
            self._check_pr_description(context.body),
            self._check_linked_issue(context.body),
            self._check_test_mention(context.body),
            self._check_breaking_change_mention(context.body, context.diff),
            self._check_diff_size(context.diff),
            self._check_tests_included(context.diff),
            self._check_single_purpose(context.diff),
        ]
        return QualityReport.from_checks(checks)

    # ------------------------------------------------------------------
    # PR-specific checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_pr_title_convention(title: str) -> QualityCheck:
        """Check for conventional commit format (feat|fix|docs|...:)."""
        conventional = re.compile(
            r"^(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
            r"(?:\(.+?\))?!?:\s",
            re.IGNORECASE,
        )
        if conventional.match(title):
            return QualityCheck("title-convention", 10, 10, "Title follows conventional commit format")
        return QualityCheck("title-convention", 3, 10, "Title does not follow conventional commit format")

    @staticmethod
    def _check_pr_description(body: str) -> QualityCheck:
        """Check for 'why' and 'what changed' context in the description."""
        if not body:
            return QualityCheck("pr-description", 0, 10, "No PR description provided")

        has_why = bool(
            re.search(
                r"\bwhy\b|motivation|reason|background|context|problem",
                body,
                re.IGNORECASE,
            )
        )
        has_what = bool(
            re.search(
                r"\bwhat\s+changed\b|changes?\b|summary|overview|description",
                body,
                re.IGNORECASE,
            )
        )

        if has_why and has_what:
            return QualityCheck("pr-description", 10, 10, "Description covers why and what changed")
        if has_why or has_what:
            return QualityCheck("pr-description", 5, 10, "Description partially explains the change")
        return QualityCheck("pr-description", 2, 10, "Description lacks why/what context")

    @staticmethod
    def _check_linked_issue(body: str) -> QualityCheck:
        """Check for 'closes #N', 'fixes #N', or issue URLs."""
        if not body:
            return QualityCheck("linked-issue", 0, 10, "No linked issue")

        issue_link = re.compile(
            r"(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#\d+|"
            r"https?://github\.com/[\w.-]+/[\w.-]+/issues/\d+",
            re.IGNORECASE,
        )
        if issue_link.search(body):
            return QualityCheck("linked-issue", 10, 10, "Issue linked in PR description")
        # Bare #NNN reference
        if re.search(r"#\d{1,6}\b", body):
            return QualityCheck("linked-issue", 5, 10, "Issue reference found but not explicitly linked")
        return QualityCheck("linked-issue", 0, 10, "No linked issue")

    @staticmethod
    def _check_test_mention(body: str) -> QualityCheck:
        """Check for test-related mentions in the body."""
        if not body:
            return QualityCheck("test-mention", 0, 5, "No test mention")

        test_words = re.compile(
            r"\btested?\b|\btesting\b|\bcoverage\b|\bunit\s*test|\bspec\b",
            re.IGNORECASE,
        )
        if test_words.search(body):
            return QualityCheck("test-mention", 5, 5, "Testing mentioned in description")
        return QualityCheck("test-mention", 0, 5, "No testing mentioned")

    @staticmethod
    def _check_breaking_change_mention(body: str, diff: str | None) -> QualityCheck:
        """If diff removes exports, check body mentions 'breaking change'."""
        if not diff:
            return QualityCheck("breaking-change", 5, 5, "No diff to check for breaking changes")

        removed_exports = re.findall(r"^-\s*(?:export\s|module\.exports)", diff, re.MULTILINE)
        if not removed_exports:
            return QualityCheck("breaking-change", 5, 5, "No removed exports detected")

        mentions_breaking = bool(re.search(r"breaking\s+change", body or "", re.IGNORECASE))
        if mentions_breaking:
            return QualityCheck("breaking-change", 5, 5, "Breaking change acknowledged in description")
        return QualityCheck(
            "breaking-change",
            0,
            5,
            "Removed exports detected but no breaking change mention",
        )

    @staticmethod
    def _check_diff_size(diff: str | None) -> QualityCheck:
        """Evaluate the size of the diff."""
        if not diff:
            return QualityCheck("diff-size", 5, 10, "No diff provided")

        changed_lines = sum(1 for line in diff.split("\n") if line.startswith("+") or line.startswith("-"))

        if changed_lines > 1000:
            return QualityCheck("diff-size", 2, 10, f"Very large diff ({changed_lines} changed lines)")
        if changed_lines > 500:
            return QualityCheck("diff-size", 5, 10, f"Large diff ({changed_lines} changed lines)")
        return QualityCheck("diff-size", 10, 10, f"Reasonable diff size ({changed_lines} changed lines)")

    @staticmethod
    def _check_tests_included(diff: str | None) -> QualityCheck:
        """Check if the diff includes changes to test/spec files.

        Detects test files across languages and monorepo layouts:
        - Singular ``test/`` and plural ``tests/`` directories anywhere
        - ``__tests__/`` (Jest convention)
        - ``spec/`` and ``testing/`` directories
        - File names: ``test_x``, ``x_test.``, ``x.test.``, ``x.spec.``
        - Modern web extensions: ``.test.tsx``, ``.spec.tsx``

        Uses path separators to avoid matching substrings like "contestant".
        """
        if not diff:
            return QualityCheck("tests-included", 0, 10, "No diff provided")

        # Match the +++ b/<path> diff header lines and check the path.
        # Anchoring on 'b/' lets us treat the path as a fresh string,
        # so leading directories like 'spec/...' are also caught.
        test_file_pattern = re.compile(
            r"^\+{3}\s+b/(?:[^\s]*/)?(?:"
            r"tests?/|"  # /test/ or /tests/ as a path component
            r"__tests__/|"  # jest convention
            r"spec/|"  # ruby/RSpec convention
            r"testing/|"  # python testing/ subdir
            r"test_[^/\s]+|"  # filename starts with test_
            r"[^/\s]+_test\.[^/\s]+|"  # filename like x_test.go
            r"[^/\s]+\.test\.[^/\s]+|"  # filename like x.test.ts
            r"[^/\s]+\.spec\.[^/\s]+"  # filename like x.spec.ts
            r")",
            re.MULTILINE | re.IGNORECASE,
        )
        if test_file_pattern.search(diff):
            return QualityCheck("tests-included", 10, 10, "Test files included in diff")
        return QualityCheck("tests-included", 0, 10, "No test files in diff")

    @staticmethod
    def _check_single_purpose(diff: str | None) -> QualityCheck:
        """Check how many directories the diff spans to gauge focus."""
        if not diff:
            return QualityCheck("single-purpose", 5, 10, "No diff provided")

        file_paths = re.findall(r"^\+{3}\s+b/(.+)$", diff, re.MULTILINE)
        directories = {path.rsplit("/", 1)[0] if "/" in path else "." for path in file_paths}

        dir_count = len(directories)
        if dir_count <= 3:
            return QualityCheck(
                "single-purpose",
                10,
                10,
                f"Changes span {dir_count} directories -- focused",
            )
        if dir_count <= 7:
            return QualityCheck(
                "single-purpose",
                5,
                10,
                f"Changes span {dir_count} directories -- somewhat broad",
            )
        return QualityCheck(
            "single-purpose",
            2,
            10,
            f"Changes span {dir_count} directories -- consider splitting",
        )
