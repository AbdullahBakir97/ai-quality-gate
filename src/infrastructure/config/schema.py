"""Pydantic models for per-repository configuration (.github/ai-gate.yml)."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "AIConfig",
    "QualityConfig",
    "AnalyzeConfig",
    "LabelsConfig",
    "ExemptConfig",
    "AppConfig",
]


class AIConfig(BaseModel):
    """Thresholds and action for AI-content detection."""

    warn: int = Field(default=50, ge=0, le=100)
    fail: int = Field(default=80, ge=0, le=100)
    action: str = Field(default="comment")


class QualityConfig(BaseModel):
    """Thresholds and action for contribution quality scoring."""

    minimum: int = Field(default=30, ge=0, le=100)
    action: str = Field(default="comment")


class AnalyzeConfig(BaseModel):
    """Which contribution types the app should analyse."""

    issues: bool = True
    pull_requests: bool = True
    comments: bool = False


class LabelsConfig(BaseModel):
    """Label names applied by the app."""

    ai_detected: str = "ai-generated"
    ai_warning: str = "ai-suspected"
    low_quality: str = "low-quality"
    high_quality: str = "high-quality"


class ExemptConfig(BaseModel):
    """Users, labels, and bot accounts exempt from analysis."""

    users: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=lambda: ["bot"])
    bots: bool = True


class AppConfig(BaseModel):
    """Top-level per-repository application configuration."""

    enabled: bool = True
    ai: AIConfig = Field(default_factory=AIConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    analyze: AnalyzeConfig = Field(default_factory=AnalyzeConfig)
    labels: LabelsConfig = Field(default_factory=LabelsConfig)
    exempt: ExemptConfig = Field(default_factory=ExemptConfig)
