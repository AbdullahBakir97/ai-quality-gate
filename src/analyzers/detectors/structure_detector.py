"""Structure-based AI content detector -- paragraph uniformity, list patterns, etc."""

import re
import statistics

from src.analyzers.patterns.registry import PatternRegistry
from src.domain.entities import Signal
from src.domain.enums import SignalType

from .base import BaseDetector

__all__ = ["StructureDetector"]


class StructureDetector(BaseDetector):
    """Analyzes text structure to detect AI-generated writing patterns."""

    def __init__(self, registry: PatternRegistry) -> None:
        self._registry = registry

    async def detect(self, text: str, *, diff: str | None = None) -> list[Signal]:
        """Return structural signals found in *text*."""
        signals: list[Signal] = []

        # 1. Run any STRUCTURAL patterns registered in the registry
        for pattern_def in self._registry.get_by_type(SignalType.STRUCTURAL):
            matches = pattern_def.pattern.findall(text)
            if matches:
                signals.append(
                    Signal(
                        type=pattern_def.signal_type,
                        pattern=pattern_def.label,
                        description=pattern_def.description or f"Structural pattern: {pattern_def.label}",
                        weight=pattern_def.weight,
                        occurrences=len(matches),
                    )
                )

        # 2. Paragraph uniformity -- AI text tends toward uniform paragraph lengths
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) >= 3:
            lengths = [len(p.split()) for p in paragraphs]
            mean = statistics.mean(lengths)
            if mean > 0:
                cv = statistics.stdev(lengths) / mean if len(lengths) > 1 else 0
                if cv < 0.15:
                    signals.append(
                        Signal(
                            type=SignalType.STRUCTURAL,
                            pattern="uniform-paragraphs",
                            description="Paragraphs are suspiciously uniform in length",
                            weight=0.3,
                            occurrences=1,
                        )
                    )

        # 3. Excessive bullet/numbered lists
        list_items = re.findall(r"^[\s]*[-*\d+.]\s", text, re.MULTILINE)
        total_lines = self.line_count(text)
        if total_lines > 0 and len(list_items) / total_lines > 0.5:
            signals.append(
                Signal(
                    type=SignalType.STRUCTURAL,
                    pattern="excessive-lists",
                    description="More than half of lines are list items",
                    weight=0.2,
                    occurrences=len(list_items),
                )
            )

        # 4. Header-heavy structure (many markdown headers relative to content)
        headers = re.findall(r"^#{1,6}\s", text, re.MULTILINE)
        if total_lines > 0 and len(headers) >= 4 and len(headers) / total_lines > 0.2:
            signals.append(
                Signal(
                    type=SignalType.STRUCTURAL,
                    pattern="header-heavy",
                    description="Unusually high ratio of markdown headers to content",
                    weight=0.15,
                    occurrences=len(headers),
                )
            )

        # 5. Formulaic section pattern (e.g. Header -> paragraph -> list, repeated)
        section_pattern = re.compile(r"^#{1,6}\s.+\n\n.+\n\n[-*]\s", re.MULTILINE)
        formulaic = section_pattern.findall(text)
        if len(formulaic) >= 3:
            signals.append(
                Signal(
                    type=SignalType.STRUCTURAL,
                    pattern="formulaic-sections",
                    description="Repeated header-paragraph-list structure typical of AI",
                    weight=0.25,
                    occurrences=len(formulaic),
                )
            )

        return signals
