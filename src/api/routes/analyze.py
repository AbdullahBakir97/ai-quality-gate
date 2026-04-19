"""Public analysis endpoint for the dashboard demo."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from src.api.dependencies import get_orchestrator
from src.api.schemas import AIDetectionResult, AnalyzeRequest, AnalyzeResponse, QualityResult
from src.application.orchestrator import AnalysisOrchestrator
from src.domain.entities import ContributionContext
from src.domain.enums import ContributionType

__all__ = ["router"]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(
    request: AnalyzeRequest,
    orchestrator: AnalysisOrchestrator = Depends(get_orchestrator),
) -> AnalyzeResponse:
    """Run AI detection and quality scoring on arbitrary text.

    This endpoint is intended for the interactive dashboard demo and
    does not require GitHub authentication.

    Args:
        request: The analysis request containing text, title, and type.
        orchestrator: The analysis orchestrator (injected).

    Returns:
        An :class:`AnalyzeResponse` with AI detection and quality results.
    """
    contribution_type = ContributionType.PULL_REQUEST if request.type == "pull_request" else ContributionType.ISSUE

    context = ContributionContext(
        title=request.title or "Untitled",
        body=request.text,
        author="anonymous",
        labels=[],
        is_bot=False,
        contribution_type=contribution_type,
        number=0,
        repo_owner="demo",
        repo_name="demo",
    )

    result = await orchestrator.analyze(context)

    return AnalyzeResponse(
        ai_detection=AIDetectionResult(
            score=result.ai_score,
            confidence=result.ai_confidence.value,
            is_likely_ai=result.is_likely_ai,
            signals=[
                {
                    "type": s.type.value,
                    "pattern": s.pattern,
                    "description": s.description,
                    "weight": s.contribution,
                }
                for s in result.ai_signals[:10]
            ],
        ),
        quality=QualityResult(
            score=result.quality_report.score,
            grade=result.quality_report.grade.value,
            checks=[
                {
                    "name": c.name,
                    "score": c.score,
                    "max_score": c.max_score,
                    "detail": c.detail,
                }
                for c in result.quality_report.checks
            ],
        ),
    )
