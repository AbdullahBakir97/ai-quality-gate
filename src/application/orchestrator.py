"""Analysis orchestrator — coordinates AI detection and quality scoring."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from src.domain.entities import AnalysisResult, ContributionContext, Signal
from src.domain.enums import ContributionType
from src.domain.interfaces import IDetector, IScorer

if TYPE_CHECKING:
    from src.analyzers.aggregator import SignalAggregator

__all__ = ["AnalysisOrchestrator"]

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    """Coordinates AI detection and quality scoring into a unified analysis.

    Runs all detectors concurrently, aggregates their signals, then
    invokes the appropriate scorer for the contribution type.
    """

    def __init__(
        self,
        detectors: list[IDetector],
        issue_scorer: IScorer,
        pr_scorer: IScorer,
        aggregator: SignalAggregator,
    ) -> None:
        self._detectors = detectors
        self._issue_scorer = issue_scorer
        self._pr_scorer = pr_scorer
        self._aggregator = aggregator

    async def analyze(self, context: ContributionContext) -> AnalysisResult:
        """Run a full analysis on the given contribution.

        Args:
            context: The contribution context containing title, body, diff, etc.

        Returns:
            A complete :class:`AnalysisResult` with AI scores and quality report.
        """
        text = f"{context.title}\n\n{context.body or ''}"

        # Run all detectors concurrently
        detector_results: list[list[Signal]] = await asyncio.gather(
            *[d.detect(text, diff=context.diff) for d in self._detectors]
        )
        all_signals: list[Signal] = [s for signals in detector_results for s in signals]

        ai_score, confidence, is_likely_ai = self._aggregator.aggregate(all_signals, text)

        # Run the appropriate scorer based on contribution type
        scorer = self._pr_scorer if context.contribution_type == ContributionType.PULL_REQUEST else self._issue_scorer
        quality_report = await scorer.score(context)

        logger.info(
            "Analysis complete for %s/%s#%d: ai_score=%d, quality=%d",
            context.repo_owner,
            context.repo_name,
            context.number,
            ai_score,
            quality_report.score,
        )

        return AnalysisResult(
            ai_score=ai_score,
            ai_confidence=confidence,
            ai_signals=sorted(all_signals, key=lambda s: s.contribution, reverse=True),
            is_likely_ai=is_likely_ai,
            quality_report=quality_report,
            contribution_type=context.contribution_type,
        )
