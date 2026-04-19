"""Issue quality scorer -- evaluates GitHub issues against quality criteria."""

import re

from src.domain.entities import ContributionContext, QualityCheck, QualityReport

from .base import BaseScorer

__all__ = ["IssueScorer"]


class IssueScorer(BaseScorer):
    """Scores GitHub issues on completeness, clarity, and actionability."""

    async def score(self, context: ContributionContext) -> QualityReport:
        """Run all quality checks and return an aggregated report."""
        checks: list[QualityCheck] = [
            self._check_title_length(context.title),
            self._check_title_specificity(context.title),
            self._check_body_presence(context.body),
            self._check_body_length(context.body),
            self._check_reproduction_steps(context.body),
            self._check_environment_info(context.body),
            self._check_code_snippets(context.body),
            self._check_screenshots(context.body),
            self._check_search_evidence(context.body),
        ]
        return QualityReport.from_checks(checks)

    # ------------------------------------------------------------------
    # Issue-specific checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_reproduction_steps(body: str) -> QualityCheck:
        """Check for steps to reproduce, expected/actual behavior, or numbered steps."""
        if not body:
            return QualityCheck("reproduction-steps", 0, 15, "No reproduction steps provided")

        has_steps_header = bool(
            re.search(
                r"steps?\s+to\s+reproduce|how\s+to\s+reproduce|reproduction\s+steps",
                body,
                re.IGNORECASE,
            )
        )
        has_expected_actual = bool(re.search(r"expected\s+(?:behavior|result|output)", body, re.IGNORECASE)) and bool(
            re.search(r"actual\s+(?:behavior|result|output)", body, re.IGNORECASE)
        )
        has_numbered_steps = bool(re.search(r"^\s*\d+[.)]\s+\S", body, re.MULTILINE))

        if has_steps_header or has_expected_actual:
            return QualityCheck("reproduction-steps", 15, 15, "Reproduction steps provided")
        if has_numbered_steps:
            return QualityCheck("reproduction-steps", 10, 15, "Numbered steps found (consider labeling them)")
        return QualityCheck("reproduction-steps", 0, 15, "No reproduction steps provided")

    @staticmethod
    def _check_environment_info(body: str) -> QualityCheck:
        """Check for version, OS, browser, or runtime environment mentions."""
        if not body:
            return QualityCheck("environment-info", 0, 10, "No environment info provided")

        env_patterns = [
            re.compile(r"\b(?:version|ver\.?)\s*[:\s]?\s*\d", re.IGNORECASE),
            re.compile(r"\b(?:windows|macos|mac\s?os|linux|ubuntu|debian)\b", re.IGNORECASE),
            re.compile(r"\b(?:chrome|firefox|safari|edge|opera)\b", re.IGNORECASE),
            re.compile(r"\b(?:node|python|java|ruby|go|rust|php)\s*\d", re.IGNORECASE),
            re.compile(r"\b(?:npm|pip|yarn|pnpm|cargo)\s", re.IGNORECASE),
            re.compile(r"\bOS\s*:", re.IGNORECASE),
        ]

        matches = sum(1 for p in env_patterns if p.search(body))
        if matches >= 2:
            return QualityCheck("environment-info", 10, 10, "Environment details provided")
        if matches == 1:
            return QualityCheck("environment-info", 5, 10, "Partial environment info provided")
        return QualityCheck("environment-info", 0, 10, "No environment info provided")

    @staticmethod
    def _check_screenshots(body: str) -> QualityCheck:
        """Check for image markdown or img tags."""
        if not body:
            return QualityCheck("screenshots", 0, 5, "No screenshots")

        has_image = bool(
            re.search(
                r"!\[.*?\]\(.*?\)|<img\s|https?://\S+\.(?:png|jpg|jpeg|gif|svg|webp)",
                body,
                re.IGNORECASE,
            )
        )
        return QualityCheck(
            "screenshots",
            5 if has_image else 0,
            5,
            "Screenshots/images included" if has_image else "No screenshots",
        )

    @staticmethod
    def _check_search_evidence(body: str) -> QualityCheck:
        """Check for evidence the author searched for duplicates."""
        if not body:
            return QualityCheck("search-evidence", 0, 5, "No search evidence")

        search_signals = [
            re.compile(r"\bsearched?\b", re.IGNORECASE),
            re.compile(r"\brelated\s+issue", re.IGNORECASE),
            re.compile(r"#\d{1,6}\b"),
            re.compile(r"\bduplicate\b", re.IGNORECASE),
            re.compile(r"\bexisting\s+issue", re.IGNORECASE),
        ]

        if any(p.search(body) for p in search_signals):
            return QualityCheck("search-evidence", 5, 5, "References to related issues or prior search")
        return QualityCheck("search-evidence", 0, 5, "No search evidence")
