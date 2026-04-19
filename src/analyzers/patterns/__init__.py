"""Pattern definitions and registry for AI content detection.

This package provides the central ``PatternRegistry`` and factory functions
that populate it with all built-in detection patterns.
"""

from src.analyzers.patterns.code_patterns import get_code_patterns
from src.analyzers.patterns.hallucination import get_hallucination_patterns
from src.analyzers.patterns.phrasing import get_phrasing_patterns
from src.analyzers.patterns.registry import PatternDefinition, PatternRegistry
from src.analyzers.patterns.structural import StructuralPattern, get_structural_patterns
from src.analyzers.patterns.vocabulary import get_vocabulary_patterns

__all__ = [
    "PatternDefinition",
    "PatternRegistry",
    "StructuralPattern",
    "get_code_patterns",
    "get_hallucination_patterns",
    "get_phrasing_patterns",
    "get_structural_patterns",
    "get_vocabulary_patterns",
    "register_default_patterns",
]


def register_default_patterns(registry: PatternRegistry) -> None:
    """Register all built-in patterns with the registry.

    Regex-based vocabulary and phrasing patterns are added directly to
    the registry.  Structural, code, and hallucination patterns use
    callable test functions rather than regex and are stored separately
    by the caller.
    """
    registry.register_many(get_vocabulary_patterns())
    registry.register_many(get_phrasing_patterns())
    # structural, code, hallucination patterns stored separately
    # since they use callable test functions not regex
