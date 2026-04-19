"""Core domain entities for the AI Quality Gate application."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .enums import Confidence, ContributionType, Grade, SignalType

__all__ = [
    "AnalysisResult",
    "ContributionContext",
    "QualityCheck",
    "QualityReport",
    "Signal",
]


@dataclass(slots=True)
class Signal:
    """A single detected indicator of AI-generated content."""

    type: SignalType
    pattern: str
    description: str
    weight: float
    occurrences: int = 1

    @property
    def contribution(self) -> float:
        """Weighted contribution capped at 3x the base weight."""
        return min(self.weight * self.occurrences, self.weight * 3)


@dataclass(slots=True)
class QualityCheck:
    """Result of a single quality assessment criterion."""

    name: str
    score: int
    max_score: int
    detail: str

    @property
    def passed(self) -> bool:
        """Whether this check achieved its maximum score."""
        return self.score == self.max_score

    @property
    def failed(self) -> bool:
        """Whether this check scored zero."""
        return self.score == 0


@dataclass(slots=True)
class QualityReport:
    """Aggregated quality assessment across all checks."""

    score: int
    grade: Grade
    checks: list[QualityCheck]

    @property
    def passed_checks(self) -> list[QualityCheck]:
        """Checks that achieved their maximum score."""
        return [c for c in self.checks if c.passed]

    @property
    def failed_checks(self) -> list[QualityCheck]:
        """Checks that scored zero."""
        return [c for c in self.checks if c.failed]

    @property
    def partial_checks(self) -> list[QualityCheck]:
        """Checks that scored between zero and maximum (exclusive)."""
        return [c for c in self.checks if 0 < c.score < c.max_score]

    @classmethod
    def from_checks(cls, checks: list[QualityCheck]) -> QualityReport:
        """Build a report by computing a normalized score and grade from checks."""
        total_max = sum(c.max_score for c in checks)
        total_score = sum(c.score for c in checks)
        normalized = round(total_score / total_max * 100) if total_max > 0 else 0

        match normalized:
            case n if n >= 90:
                grade = Grade.A
            case n if n >= 80:
                grade = Grade.B
            case n if n >= 70:
                grade = Grade.C
            case n if n >= 60:
                grade = Grade.D
            case _:
                grade = Grade.F

        return cls(score=normalized, grade=grade, checks=checks)


@dataclass(slots=True)
class ContributionContext:
    """Contextual data for a GitHub contribution under analysis."""

    title: str
    body: str
    author: str
    labels: list[str]
    is_bot: bool
    contribution_type: ContributionType
    number: int
    repo_owner: str
    repo_name: str
    diff: str | None = None
    head_sha: str | None = None


@dataclass(slots=True)
class AnalysisResult:
    """Complete analysis output combining AI detection and quality assessment."""

    ai_score: int
    ai_confidence: Confidence
    ai_signals: list[Signal]
    is_likely_ai: bool
    quality_report: QualityReport
    contribution_type: ContributionType
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
