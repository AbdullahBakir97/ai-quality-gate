"""Base scorer with shared quality check methods."""

import re
from abc import ABC

from src.domain.entities import QualityCheck
from src.domain.interfaces import IScorer

__all__ = ["BaseScorer"]


class BaseScorer(IScorer, ABC):
    """Provides reusable quality checks shared between issue and PR scorers."""

    def _check_title_length(self, title: str) -> QualityCheck:
        """Evaluate whether the title length is reasonable."""
        length = len(title)
        if length == 0:
            return QualityCheck("title-present", 0, 10, "No title provided")
        if length < 10:
            return QualityCheck("title-length", 3, 10, "Title too short")
        if length > 100:
            return QualityCheck("title-length", 5, 10, "Title too long")
        return QualityCheck("title-length", 10, 10, "Good title length")

    def _check_title_specificity(self, title: str) -> QualityCheck:
        """Evaluate whether the title is specific rather than vague."""
        vague = [
            re.compile(
                r"^(bug|fix|update|change|issue|problem|error|help|question|feature|request)$",
                re.IGNORECASE,
            ),
            re.compile(
                r"^(please help|doesn'?t work|broken|not working|why)$",
                re.IGNORECASE,
            ),
            re.compile(
                r"^(test|wip|draft|todo|tmp|temp)$",
                re.IGNORECASE,
            ),
        ]
        for pattern in vague:
            if pattern.match(title.strip()):
                return QualityCheck("title-specificity", 0, 10, f'Vague title: "{title}"')

        has_specifics = bool(re.search(r"[A-Z][a-z]+[A-Z]|_[a-z]|[a-z]\(\)|\.{1}[a-z]", title))
        score = 10 if has_specifics else 6
        detail = "Title references specific code/component" if has_specifics else "Title could be more specific"
        return QualityCheck("title-specificity", score, 10, detail)

    def _check_body_presence(self, body: str) -> QualityCheck:
        """Check that a description body is provided."""
        if not body or not body.strip():
            return QualityCheck("body-present", 0, 15, "No description provided")
        return QualityCheck("body-present", 15, 15, "Description provided")

    def _check_body_length(self, body: str) -> QualityCheck:
        """Evaluate whether the body has adequate detail."""
        words = len(body.split()) if body else 0
        if words < 10:
            return QualityCheck("body-length", 2, 10, "Description too brief")
        if words < 30:
            return QualityCheck("body-length", 5, 10, "Description could be more detailed")
        if words > 2000:
            return QualityCheck("body-length", 5, 10, "Description excessively long")
        return QualityCheck("body-length", 10, 10, "Good description length")

    def _check_code_snippets(self, body: str) -> QualityCheck:
        """Check whether the body includes code snippets."""
        has_code = bool(re.search(r"```[\s\S]*?```|`[^`]+`", body or ""))
        return QualityCheck(
            "code-snippets",
            10 if has_code else 0,
            10,
            "Code snippets included" if has_code else "No code snippets",
        )
