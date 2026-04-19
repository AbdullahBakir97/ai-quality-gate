"""AI vocabulary patterns -- words that AI models overuse but humans rarely do."""

import re

from src.domain.enums import SignalType
from src.analyzers.patterns.registry import PatternDefinition

__all__ = ["get_vocabulary_patterns"]


def get_vocabulary_patterns() -> list[PatternDefinition]:
    """Return pattern definitions for AI-overused vocabulary words.

    Each pattern targets a single word known to appear far more frequently
    in AI-generated text than in human writing.  Weights reflect how
    strongly the word signals AI authorship.
    """
    signal = SignalType.AI_VOCABULARY
    raw: list[tuple[str, float, str]] = [
        ("delve", 0.3, "Strongly associated with AI-generated text"),
        ("leverage", 0.15, "Overused in AI business writing"),
        ("foster", 0.15, "Common AI hedging word"),
        ("tapestry", 0.25, "Rarely used by humans in non-literary contexts"),
        ("holistic", 0.15, "AI buzzword for comprehensive"),
        ("seamless(?:ly)?", 0.15, "AI-favored transition descriptor"),
        ("robust", 0.1, "Generic AI quality descriptor"),
        ("pivotal", 0.2, "AI emphasis word"),
        ("underscore", 0.15, "AI synonym for emphasize"),
        ("paramount", 0.2, "AI superlative modifier"),
        ("meticulous(?:ly)?", 0.2, "AI precision descriptor"),
        ("intricate(?:ly)?", 0.15, "AI complexity descriptor"),
        ("commendable", 0.2, "AI praise word"),
        ("noteworthy", 0.25, "AI attention-directing word"),
        ("groundbreaking", 0.15, "AI hyperbole word"),
        ("furthermore", 0.1, "AI transition word"),
        ("additionally", 0.1, "AI additive transition"),
        ("comprehensive", 0.1, "AI completeness descriptor"),
        ("utilize", 0.15, "AI synonym for use"),
        ("facilitate", 0.15, "AI synonym for help"),
        ("endeavor", 0.2, "AI formal synonym for try"),
        ("multifaceted", 0.25, "AI complexity descriptor"),
        ("nuanced", 0.15, "AI sophistication descriptor"),
        ("streamline", 0.15, "AI efficiency buzzword"),
    ]

    return [
        PatternDefinition(
            pattern=re.compile(rf"\b{word}\b", re.IGNORECASE),
            weight=weight,
            signal_type=signal,
            label=word.replace("(?:", "(").replace(")?", ")?"),
            description=desc,
        )
        for word, weight, desc in raw
    ]
