"""Code pattern detector -- analyzes PR diffs for AI code patterns."""

import re

from src.analyzers.patterns.registry import PatternRegistry
from src.domain.entities import Signal
from src.domain.enums import SignalType

from .base import BaseDetector

__all__ = ["CodeDetector"]


class CodeDetector(BaseDetector):
    """Analyzes PR diffs for patterns typical of AI-generated code."""

    def __init__(self, registry: PatternRegistry) -> None:
        self._registry = registry

    async def detect(self, text: str, *, diff: str | None = None) -> list[Signal]:
        """Return code-level signals found in *diff*.

        Only runs if a diff is provided; returns an empty list otherwise.
        """
        if not diff:
            return []

        signals: list[Signal] = []

        # 1. Run any CODE patterns from the registry
        for pattern_def in self._registry.get_by_type(SignalType.CODE):
            matches = pattern_def.pattern.findall(diff)
            if matches:
                signals.append(
                    Signal(
                        type=pattern_def.signal_type,
                        pattern=pattern_def.label,
                        description=pattern_def.description
                        or f"Code pattern: {pattern_def.label}",
                        weight=pattern_def.weight,
                        occurrences=len(matches),
                    )
                )

        # 2. Excessive inline comments (AI tends to over-comment)
        added_lines = [
            line[1:] for line in diff.split("\n") if line.startswith("+")
        ]
        comment_patterns = re.compile(
            r"(?://\s.+|#\s.+|/\*.*\*/|<!--.*-->)"
        )
        comment_count = sum(
            1 for line in added_lines if comment_patterns.search(line)
        )
        if len(added_lines) > 0 and comment_count / len(added_lines) > 0.4:
            signals.append(
                Signal(
                    type=SignalType.CODE,
                    pattern="excessive-comments",
                    description="Unusually high ratio of comments in added code",
                    weight=0.2,
                    occurrences=comment_count,
                )
            )

        # 3. TODO/FIXME placeholder comments
        placeholder_matches = re.findall(
            r"(?:TODO|FIXME|HACK|XXX):\s*(?:implement|add|fix|update|handle)\b",
            diff,
            re.IGNORECASE,
        )
        if placeholder_matches:
            signals.append(
                Signal(
                    type=SignalType.CODE,
                    pattern="placeholder-todos",
                    description="Generic TODO/FIXME placeholders typical of AI scaffolding",
                    weight=0.15,
                    occurrences=len(placeholder_matches),
                )
            )

        # 4. Overly descriptive variable/function names
        verbose_names = re.findall(
            r"\b[a-z]+(?:[A-Z][a-z]+){4,}\b", diff
        )
        if len(verbose_names) >= 3:
            signals.append(
                Signal(
                    type=SignalType.CODE,
                    pattern="verbose-identifiers",
                    description="Excessively long camelCase identifiers typical of AI",
                    weight=0.1,
                    occurrences=len(verbose_names),
                )
            )

        # 5. Boilerplate try/except or try/catch blocks
        try_blocks = re.findall(
            r"try\s*[:{][\s\S]{0,200}(?:except|catch)\s*(?:\([^)]*\))?\s*[:{]",
            diff,
        )
        if len(try_blocks) >= 3:
            signals.append(
                Signal(
                    type=SignalType.CODE,
                    pattern="boilerplate-error-handling",
                    description="Multiple generic try/catch blocks suggesting AI scaffolding",
                    weight=0.15,
                    occurrences=len(try_blocks),
                )
            )

        # 6. Import-heavy files (AI tends to import everything)
        import_lines = re.findall(
            r"^\+\s*(?:import |from .+ import |const .+ = require)",
            diff,
            re.MULTILINE,
        )
        if len(import_lines) >= 15:
            signals.append(
                Signal(
                    type=SignalType.CODE,
                    pattern="heavy-imports",
                    description="Large number of import statements in a single diff",
                    weight=0.1,
                    occurrences=len(import_lines),
                )
            )

        return signals
