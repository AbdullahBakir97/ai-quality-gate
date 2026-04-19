"""Pydantic request and response models for the API layer."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "AIDetectionResult",
    "AnalyzeRequest",
    "AnalyzeResponse",
    "HealthResponse",
    "QualityResult",
    "WebhookResponse",
]


class AnalyzeRequest(BaseModel):
    """Request body for the ``/api/v1/analyze`` endpoint."""

    text: str = Field(..., min_length=1, description="Content text to analyse")
    title: str = Field(default="", description="Contribution title")
    type: str = Field(default="issue", description="Contribution type: 'issue' or 'pull_request'")


class AIDetectionResult(BaseModel):
    """AI detection scores within an :class:`AnalyzeResponse`."""

    score: int
    confidence: str
    is_likely_ai: bool
    signals: list[dict[str, object]] = Field(default_factory=list)


class QualityResult(BaseModel):
    """Quality assessment within an :class:`AnalyzeResponse`."""

    score: int
    grade: str
    checks: list[dict[str, object]] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    """Response body for the ``/api/v1/analyze`` endpoint."""

    ai_detection: AIDetectionResult
    quality: QualityResult


class HealthResponse(BaseModel):
    """Response body for the ``/health`` endpoint."""

    status: str = "ok"
    uptime: float = 0.0
    version: str = "1.0.0"


class WebhookResponse(BaseModel):
    """Response body for the ``/webhook`` endpoint."""

    received: bool = True
