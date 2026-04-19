"""Core domain layer — entities, enums, interfaces, and exceptions."""

from src.core.entities import (
    AnalysisResult,
    ContributionContext,
    QualityCheck,
    QualityReport,
    Signal,
)
from src.core.enums import (
    ActionType,
    Confidence,
    ContributionType,
    Grade,
    SignalType,
)
from src.core.exceptions import (
    AIQualityGateError,
    AnalysisError,
    ConfigurationError,
    GitHubAPIError,
    WebhookValidationError,
)
from src.core.interfaces import (
    IActionHandler,
    IConfigLoader,
    IDetector,
    IGitHubClient,
    IScorer,
)

__all__ = [
    "AIQualityGateError",
    "ActionType",
    "AnalysisError",
    "AnalysisResult",
    "Confidence",
    "ConfigurationError",
    "ContributionContext",
    "ContributionType",
    "GitHubAPIError",
    "Grade",
    "IActionHandler",
    "IConfigLoader",
    "IDetector",
    "IGitHubClient",
    "IScorer",
    "QualityCheck",
    "QualityReport",
    "Signal",
    "SignalType",
    "WebhookValidationError",
]
