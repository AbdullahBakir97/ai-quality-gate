"""Thread-safe pattern registry using the Registry design pattern."""

import re
from dataclasses import dataclass
from typing import ClassVar

from src.domain.enums import SignalType

__all__ = ["PatternDefinition", "PatternRegistry"]


@dataclass(frozen=True, slots=True)
class PatternDefinition:
    """Immutable definition of a detection pattern."""

    pattern: re.Pattern
    weight: float
    signal_type: SignalType
    label: str
    description: str = ""


class PatternRegistry:
    """Central registry for all detection patterns.

    Supports registration at runtime for extensibility (Open/Closed Principle).
    """

    _instance: ClassVar["PatternRegistry | None"] = None

    def __init__(self) -> None:
        self._patterns: dict[SignalType, list[PatternDefinition]] = {}

    def register(self, pattern_def: PatternDefinition) -> None:
        """Register a single pattern definition."""
        self._patterns.setdefault(pattern_def.signal_type, []).append(pattern_def)

    def register_many(self, patterns: list[PatternDefinition]) -> None:
        """Register multiple pattern definitions at once."""
        for p in patterns:
            self.register(p)

    def get_by_type(self, signal_type: SignalType) -> list[PatternDefinition]:
        """Return all patterns registered under the given signal type."""
        return self._patterns.get(signal_type, [])

    def get_all(self) -> list[PatternDefinition]:
        """Return all registered patterns across every signal type."""
        return [p for patterns in self._patterns.values() for p in patterns]

    @property
    def count(self) -> int:
        """Total number of registered patterns."""
        return sum(len(ps) for ps in self._patterns.values())

    def clear(self) -> None:
        """Remove all registered patterns."""
        self._patterns.clear()
