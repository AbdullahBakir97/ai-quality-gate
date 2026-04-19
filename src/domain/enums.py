"""Enumeration types for the AI Quality Gate domain."""

from enum import StrEnum

__all__ = [
    "ActionType",
    "Confidence",
    "ContributionType",
    "Grade",
    "SignalType",
]


class SignalType(StrEnum):
    """Categories of AI-generated content signals."""

    AI_VOCABULARY = "ai-vocabulary"
    AI_PHRASING = "ai-phrasing"
    STRUCTURAL = "structural"
    CODE = "code"
    HALLUCINATION = "hallucination"
    META = "meta"


class Confidence(StrEnum):
    """Confidence levels for AI detection results."""

    NONE = "none"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Grade(StrEnum):
    """Letter grades for quality assessment."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class ActionType(StrEnum):
    """Types of actions the app can take on contributions."""

    COMMENT = "comment"
    LABEL = "label"
    REQUEST_CHANGES = "request-changes"
    CLOSE = "close"


class ContributionType(StrEnum):
    """Types of GitHub contributions the app analyzes."""

    ISSUE = "issue"
    PULL_REQUEST = "pull_request"
