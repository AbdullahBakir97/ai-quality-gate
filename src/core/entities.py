"""Domain entities representing the core data structures of the AI Quality Gate system."""

from dataclasses import dataclass, field

from src.core.enums import Confidence, ContributionType, Grade, SignalType

__all__ = [
    "AnalysisResult",
    "ContributionContext",
    "QualityCheck",
    "QualityReport",
    "Signal",
]


@dataclass(frozen=True, slots=True)
class Signal:
    """An individual detection signal found during AI content analysis.

    Each signal represents a single piece of evidence suggesting AI-generated content,
    weighted by its diagnostic strength.
    """

    type: SignalType
    pattern: str
    weight: float
    description: str
    occurrences: int = 1

    @property
    def weighted_score(self) -> float:
        """Total contribution of this signal: weight multiplied by occurrence count."""
        return self.weight * self.occurrences


@dataclass(frozen=True, slots=True)
class QualityCheck:
    """Result of a single quality check within the quality assessment pipeline."""

    name: str
    score: float
    max_score: float
    detail: str

    @property
    def percentage(self) -> float:
        """Score as a percentage of the maximum possible."""
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Aggregated quality report combining multiple quality checks."""

    score: float
    grade: Grade
    checks: list[QualityCheck] = field(default_factory=list)

    @property
    def passed(self) -> list[QualityCheck]:
        """Checks that achieved their full score."""
        return [c for c in self.checks if c.score >= c.max_score]

    @property
    def failed(self) -> list[QualityCheck]:
        """Checks that did not achieve their full score."""
        return [c for c in self.checks if c.score < c.max_score]


@dataclass(frozen=True, slots=True)
class ContributionContext:
    """Context about a GitHub contribution (issue or pull request) being analyzed.

    Captures all the metadata and content needed by detectors and scorers
    to produce an analysis result.
    """

    title: str
    body: str
    author: str
    type: ContributionType
    labels: list[str] = field(default_factory=list)
    is_bot: bool = False
    diff: str | None = None

    @property
    def full_text(self) -> str:
        """Combined title and body for analysis purposes."""
        return f"{self.title}\n\n{self.body}"


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Final result of analyzing a contribution for AI-generated content and quality.

    Combines AI detection signals with quality scoring to produce a holistic assessment.
    """

    ai_score: float
    quality_score: float
    signals: list[Signal] = field(default_factory=list)
    confidence: Confidence = Confidence.NONE
    quality_report: QualityReport | None = None

    @property
    def is_likely_ai(self) -> bool:
        """Whether the content is likely AI-generated, based on score and confidence."""
        return self.ai_score >= 0.7 and self.confidence >= Confidence.MEDIUM

    @property
    def signal_count(self) -> int:
        """Total number of signals detected."""
        return len(self.signals)
