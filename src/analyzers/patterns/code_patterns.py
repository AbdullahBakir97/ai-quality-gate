"""Code and diff-specific patterns for pull-request analysis."""

from __future__ import annotations

import re

from src.analyzers.patterns.structural import StructuralPattern

__all__ = ["get_code_patterns"]

# Pre-compiled regexes for diff analysis.
_RE_ADDED_LINE = re.compile(r"^\+(?!\+\+)")
_RE_COMMENT_LINE = re.compile(r"^\+\s*(//|#|/\*|\*|<!--)")
_RE_IMPORT_LINE = re.compile(r"^\+\s*(import |from .+ import |require\(|use )")
_RE_TODO = re.compile(r"\b(?:TODO|FIXME|PLACEHOLDER)\b", re.IGNORECASE)
_RE_GENERIC_NAME = re.compile(
    r"\b(?:handleClick|fetchData|temp|data|result|value|item|obj|arr|foo|bar)\b"
)


def _excessive_comments(text: str) -> float:
    """Detect diffs where over 40% of added lines are comments."""
    added = [ln for ln in text.splitlines() if _RE_ADDED_LINE.match(ln)]
    if not added:
        return 0.0
    comments = sum(1 for ln in added if _RE_COMMENT_LINE.match(ln))
    ratio = comments / len(added)
    return 0.3 if ratio > 0.4 else 0.0


def _boilerplate_heavy(text: str) -> float:
    """Detect diffs where over 30% of added lines are imports."""
    added = [ln for ln in text.splitlines() if _RE_ADDED_LINE.match(ln)]
    if not added:
        return 0.0
    imports = sum(1 for ln in added if _RE_IMPORT_LINE.match(ln))
    ratio = imports / len(added)
    return 0.2 if ratio > 0.3 else 0.0


def _todo_placeholder(text: str) -> float:
    """Detect diffs with excessive TODO/FIXME/PLACEHOLDER markers."""
    added = [ln for ln in text.splitlines() if _RE_ADDED_LINE.match(ln)]
    if not added:
        return 0.0
    count = sum(1 for ln in added if _RE_TODO.search(ln))
    return 0.25 if count > 3 else 0.0


def _generic_variable_names(text: str) -> float:
    """Detect diffs with many generic variable/function names."""
    added = [ln for ln in text.splitlines() if _RE_ADDED_LINE.match(ln)]
    if not added:
        return 0.0
    combined = " ".join(added)
    matches = _RE_GENERIC_NAME.findall(combined)
    return 0.15 if len(matches) > 10 else 0.0


def get_code_patterns() -> list[StructuralPattern]:
    """Return all built-in code/diff detection patterns."""
    return [
        StructuralPattern(
            name="excessive_comments",
            description="Over 40% of added lines in a diff are comments",
            max_weight=0.3,
            test=_excessive_comments,
        ),
        StructuralPattern(
            name="boilerplate_heavy",
            description="Over 30% of added lines are import statements",
            max_weight=0.2,
            test=_boilerplate_heavy,
        ),
        StructuralPattern(
            name="todo_placeholder",
            description="More than 3 TODO/FIXME/PLACEHOLDER markers in added lines",
            max_weight=0.25,
            test=_todo_placeholder,
        ),
        StructuralPattern(
            name="generic_variable_names",
            description="More than 10 occurrences of generic names like handleClick, fetchData, temp",
            max_weight=0.15,
            test=_generic_variable_names,
        ),
    ]
