"""Hallucination detector -- fake references, APIs, version numbers."""

import re

from src.domain.entities import Signal
from src.domain.enums import SignalType
from src.analyzers.patterns.registry import PatternRegistry

from .base import BaseDetector

__all__ = ["HallucinationDetector"]


class HallucinationDetector(BaseDetector):
    """Detects hallucinated references, fake APIs, and suspicious version numbers."""

    def __init__(self, registry: PatternRegistry) -> None:
        self._registry = registry

    async def detect(self, text: str, *, diff: str | None = None) -> list[Signal]:
        """Return hallucination signals found in *text*."""
        signals: list[Signal] = []

        # 1. Run any HALLUCINATION patterns from the registry
        for pattern_def in self._registry.get_by_type(SignalType.HALLUCINATION):
            matches = pattern_def.pattern.findall(text)
            if matches:
                signals.append(
                    Signal(
                        type=pattern_def.signal_type,
                        pattern=pattern_def.label,
                        description=pattern_def.description
                        or f"Hallucination pattern: {pattern_def.label}",
                        weight=pattern_def.weight,
                        occurrences=len(matches),
                    )
                )

        # 2. Suspicious version numbers (e.g. v14.2.7, very specific but unlikely)
        version_refs = re.findall(
            r"\bv?\d{1,3}\.\d{1,3}\.\d{1,3}(?:\.\d{1,3})?\b", text
        )
        if len(version_refs) >= 3:
            signals.append(
                Signal(
                    type=SignalType.HALLUCINATION,
                    pattern="excessive-version-refs",
                    description="Multiple specific version numbers may be hallucinated",
                    weight=0.2,
                    occurrences=len(version_refs),
                )
            )

        # 3. Fake-looking API references (e.g. someApi.someMethod())
        api_calls = re.findall(
            r"\b[a-z][a-zA-Z]+\.[a-z][a-zA-Z]+\([^)]*\)", text
        )
        if len(api_calls) >= 5:
            signals.append(
                Signal(
                    type=SignalType.HALLUCINATION,
                    pattern="suspicious-api-refs",
                    description="Multiple API-style references that may be fabricated",
                    weight=0.15,
                    occurrences=len(api_calls),
                )
            )

        # 4. Non-existent RFC/standard references
        rfc_refs = re.findall(r"\bRFC\s?\d{4,5}\b", text, re.IGNORECASE)
        if rfc_refs:
            signals.append(
                Signal(
                    type=SignalType.HALLUCINATION,
                    pattern="rfc-references",
                    description="RFC references that may not exist",
                    weight=0.2,
                    occurrences=len(rfc_refs),
                )
            )

        # 5. Fabricated citation patterns ([1], [2], ... without actual reference list)
        inline_citations = re.findall(r"\[(\d+)\]", text)
        has_reference_section = bool(
            re.search(r"(?:references|bibliography|sources)\s*\n", text, re.IGNORECASE)
        )
        if len(inline_citations) >= 3 and not has_reference_section:
            signals.append(
                Signal(
                    type=SignalType.HALLUCINATION,
                    pattern="phantom-citations",
                    description="Inline citations without a references section",
                    weight=0.3,
                    occurrences=len(inline_citations),
                )
            )

        return signals
