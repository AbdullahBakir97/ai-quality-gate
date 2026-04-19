"""Domain-specific exceptions for the AI Quality Gate application."""

__all__ = [
    "AIQualityGateError",
    "AnalysisError",
    "ConfigurationError",
    "GitHubAPIError",
    "WebhookValidationError",
]


class AIQualityGateError(Exception):
    """Base exception for all app errors."""


class ConfigurationError(AIQualityGateError):
    """Invalid or missing configuration."""


class GitHubAPIError(AIQualityGateError):
    """GitHub API communication failure."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class WebhookValidationError(AIQualityGateError):
    """Invalid webhook signature or payload."""


class AnalysisError(AIQualityGateError):
    """Error during content analysis."""
