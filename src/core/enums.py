"""Domain enumerations for the AI Quality Gate system."""

from enum import Enum, auto

__all__ = [
    "ActionType",
    "Confidence",
    "ContributionType",
    "Grade",
    "SignalType",
]


class Confidence(Enum):
    """Confidence level for AI detection results.

    Ordered from lowest to highest — numeric values enable threshold comparisons.
    """

    NONE = 0
    MINIMAL = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4

    def __ge__(self, other: "Confidence") -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.value >= other.value

    def __gt__(self, other: "Confidence") -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.value > other.value

    def __le__(self, other: "Confidence") -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.value <= other.value

    def __lt__(self, other: "Confidence") -> bool:
        if not isinstance(other, Confidence):
            return NotImplemented
        return self.value < other.value


class Grade(Enum):
    """Letter grade for quality assessment."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"

    @classmethod
    def from_score(cls, score: float) -> "Grade":
        """Derive a grade from a normalized 0-100 score."""
        match score:
            case s if s >= 90:
                return cls.A
            case s if s >= 80:
                return cls.B
            case s if s >= 70:
                return cls.C
            case s if s >= 60:
                return cls.D
            case _:
                return cls.F


class ContributionType(Enum):
    """Type of GitHub contribution being analyzed."""

    ISSUE = auto()
    PULL_REQUEST = auto()


class ActionType(Enum):
    """Action the app can take in response to analysis results."""

    COMMENT = auto()
    LABEL = auto()
    REQUEST_CHANGES = auto()
    CLOSE = auto()


class SignalType(Enum):
    """Category of detection signal used during AI content analysis."""

    AI_VOCABULARY = auto()
    AI_PHRASING = auto()
    STRUCTURAL = auto()
    CODE = auto()
    HALLUCINATION = auto()
    META = auto()
