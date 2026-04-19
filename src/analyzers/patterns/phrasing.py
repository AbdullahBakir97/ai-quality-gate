"""AI phrasing patterns -- multi-word phrases commonly produced by AI models."""

import re

from src.domain.enums import SignalType
from src.analyzers.patterns.registry import PatternDefinition

__all__ = ["get_phrasing_patterns"]


def get_phrasing_patterns() -> list[PatternDefinition]:
    """Return pattern definitions for AI-characteristic multi-word phrases.

    These phrases are stylistic markers that appear far more often in
    AI-generated text than in organic human writing.
    """
    signal = SignalType.AI_PHRASING
    raw: list[tuple[str, float, str]] = [
        (r"it'?s worth noting", 0.3, "AI hedging opener"),
        (r"this ensures that", 0.2, "AI causal connector"),
        (r"by doing so", 0.15, "AI consequence phrase"),
        (r"I'?d be happy to", 0.4, "AI assistant politeness marker"),
        (r"here'?s a (?:breakdown|summary|overview)", 0.35, "AI structuring phrase"),
        (r"let me know if you", 0.2, "AI closing offer"),
        (r"feel free to", 0.15, "AI permission phrase"),
        (r"hope this helps", 0.4, "AI closing phrase"),
        (r"please note that", 0.15, "AI formal qualifier"),
        (r"in conclusion", 0.15, "AI essay-style closer"),
        (r"in summary", 0.1, "AI summary opener"),
        (r"overall,", 0.1, "AI summary transition"),
        (r"as a result", 0.1, "AI causal connector"),
        (r"it is important to note", 0.3, "AI emphasis phrase"),
        (r"plays a crucial role", 0.2, "AI importance phrase"),
        (r"serves as a", 0.15, "AI function descriptor"),
    ]

    return [
        PatternDefinition(
            pattern=re.compile(rf"\b{phrase}\b", re.IGNORECASE),
            weight=weight,
            signal_type=signal,
            label=phrase,
            description=desc,
        )
        for phrase, weight, desc in raw
    ]
