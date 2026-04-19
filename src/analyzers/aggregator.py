"""Signal aggregator -- combines detection signals into a final AI score."""

import re
from collections import Counter
from typing import ClassVar

from src.domain.entities import Signal
from src.domain.enums import Confidence

__all__ = ["SignalAggregator"]


class SignalAggregator:
    """Aggregates detection signals into a final AI score with confidence."""

    _FILLER_WORDS: ClassVar[set[str]] = {
        "very", "really", "just", "quite", "rather", "somewhat", "basically",
        "actually", "literally", "simply", "essentially", "overall",
        "generally", "typically", "usually", "obviously", "clearly",
        "certainly", "definitely", "absolutely", "incredibly",
    }

    def aggregate(
        self, signals: list[Signal], text: str
    ) -> tuple[int, Confidence, bool]:
        """Compute a final AI score, confidence level, and likelihood flag.

        Returns:
            A 3-tuple of ``(score, confidence, is_likely_ai)`` where *score*
            is an integer 0-100, *confidence* is a :class:`Confidence` enum
            member, and *is_likely_ai* is ``True`` when the score suggests
            AI authorship.
        """
        if not signals:
            return 0, Confidence.NONE, False

        raw_score = self._compute_raw_score(signals)
        substance_penalty = self._substance_analysis(text)
        repetition_penalty = self._repetition_analysis(text)

        adjusted = raw_score + substance_penalty + repetition_penalty
        normalized = min(round(adjusted * 25), 100)
        score = max(0, min(normalized, 100))

        confidence = self._compute_confidence(score, len(signals))
        is_likely_ai = score >= 50 and confidence in (
            Confidence.MEDIUM,
            Confidence.HIGH,
        )

        return score, confidence, is_likely_ai

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_raw_score(signals: list[Signal]) -> float:
        """Sum weighted contributions from all signals."""
        return sum(s.contribution for s in signals)

    @staticmethod
    def _compute_confidence(score: int, signal_count: int) -> Confidence:
        """Determine confidence from the score and signal count."""
        if score >= 70 and signal_count >= 5:
            return Confidence.HIGH
        if score >= 50 and signal_count >= 3:
            return Confidence.MEDIUM
        if score >= 30 and signal_count >= 2:
            return Confidence.LOW
        if signal_count >= 1:
            return Confidence.MINIMAL
        return Confidence.NONE

    def _substance_analysis(self, text: str) -> float:
        """Return a penalty (positive value) if the text has high filler ratio.

        Only applies to texts longer than 100 words.
        """
        words = text.lower().split()
        if len(words) < 100:
            return 0.0

        filler_count = sum(1 for w in words if w in self._FILLER_WORDS)
        ratio = filler_count / len(words)

        # Filler ratio > 5% adds a small penalty
        if ratio > 0.05:
            return round(ratio * 5, 2)
        return 0.0

    @staticmethod
    def _repetition_analysis(text: str) -> float:
        """Return a penalty if the text re-uses the same sentence starters.

        AI-generated text often begins consecutive sentences with the same
        word or phrase (e.g. "This", "The", "It").
        """
        sentences = re.split(r"[.!?]\s+", text)
        if len(sentences) < 5:
            return 0.0

        starters = [
            s.split()[0].lower()
            for s in sentences
            if s.strip() and s.split()
        ]
        if not starters:
            return 0.0

        counter = Counter(starters)
        most_common_count = counter.most_common(1)[0][1]
        ratio = most_common_count / len(starters)

        # If a single starter accounts for > 30% of sentences, penalize
        if ratio > 0.3:
            return round(ratio * 2, 2)
        return 0.0
