"""Pattern-based AI content detector using the PatternRegistry."""

from src.analyzers.patterns.registry import PatternRegistry
from src.domain.entities import Signal
from src.domain.enums import SignalType

from .base import BaseDetector

__all__ = ["PatternDetector"]


class PatternDetector(BaseDetector):
    """Detects AI-generated content using vocabulary and phrasing patterns."""

    def __init__(self, registry: PatternRegistry) -> None:
        self._registry = registry

    async def detect(self, text: str, *, diff: str | None = None) -> list[Signal]:
        """Scan *text* against all AI_VOCABULARY and AI_PHRASING patterns."""
        signals: list[Signal] = []

        target_types = (SignalType.AI_VOCABULARY, SignalType.AI_PHRASING)
        for signal_type in target_types:
            for pattern_def in self._registry.get_by_type(signal_type):
                matches = pattern_def.pattern.findall(text)
                if matches:
                    prefix = "AI vocabulary" if signal_type == SignalType.AI_VOCABULARY else "AI phrasing"
                    signals.append(
                        Signal(
                            type=pattern_def.signal_type,
                            pattern=pattern_def.label,
                            description=pattern_def.description or f"{prefix}: {pattern_def.label}",
                            weight=pattern_def.weight,
                            occurrences=len(matches),
                        )
                    )

        return signals
