"""Domain layer — pure business logic with zero external dependencies."""

from .enums import (
    ActionType,
    Confidence,
    ContributionType,
    Grade,
    SignalType,
)
from .entities import (
    AnalysisResult,
    ContributionContext,
    QualityCheck,
    QualityReport,
    Signal,
)
from .exceptions import (
    AIQualityGateError,
    AnalysisError,
    ConfigurationError,
    GitHubAPIError,
    WebhookValidationError,
)
from .interfaces import (
    IActionHandler,
    IConfigLoader,
    IDetector,
    IGitHubClient,
    IScorer,
)
from .value_objects import Score, Threshold

__all__ = [
    # Enums
    "ActionType",
    "Confidence",
    "ContributionType",
    "Grade",
    "SignalType",
    # Entities
    "AnalysisResult",
    "ContributionContext",
    "QualityCheck",
    "QualityReport",
    "Signal",
    # Exceptions
    "AIQualityGateError",
    "AnalysisError",
    "ConfigurationError",
    "GitHubAPIError",
    "WebhookValidationError",
    # Interfaces
    "IActionHandler",
    "IConfigLoader",
    "IDetector",
    "IGitHubClient",
    "IScorer",
    # Value Objects
    "Score",
    "Threshold",
]
