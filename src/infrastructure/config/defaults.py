"""Default configuration factory and message templates."""

from __future__ import annotations

from .schema import AppConfig

__all__ = ["MESSAGE_TEMPLATES", "DefaultConfigFactory"]


MESSAGE_TEMPLATES: dict[str, str] = {
    "ai_warning": (
        "## AI Quality Gate — AI Content Detected\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        "| AI Score | **{ai_score}%** |\n"
        "| Confidence | {confidence} |\n\n"
        "### Signals\n{signals}\n\n"
        "_This contribution has been flagged as potentially AI-generated. "
        "Please ensure the content is original and accurate._"
    ),
    "low_quality": (
        "## AI Quality Gate — Low Quality\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        "| Quality Score | **{quality_score}%** ({grade}) |\n\n"
        "### Improvements Needed\n{improvements}\n\n"
        "_Please review the suggestions above to improve your contribution._"
    ),
    "combined": (
        "## AI Quality Gate — Review Required\n\n"
        "| Metric | Value |\n"
        "|--------|-------|\n"
        "| AI Score | **{ai_score}%** ({confidence}) |\n"
        "| Quality Score | **{quality_score}%** ({grade}) |\n\n"
        "### AI Signals\n{signals}\n\n"
        "### Improvements Needed\n{improvements}\n\n"
        "_This contribution has been flagged for both AI content and quality concerns._"
    ),
}


class DefaultConfigFactory:
    """Factory that produces default :class:`AppConfig` instances."""

    @staticmethod
    def create() -> AppConfig:
        """Return a fresh default configuration."""
        return AppConfig()
