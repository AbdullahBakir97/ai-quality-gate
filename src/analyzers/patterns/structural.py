"""Structural patterns -- callable heuristics that analyse text layout and formatting."""

from __future__ import annotations

import re
import statistics
from collections.abc import Callable
from dataclasses import dataclass

__all__ = ["StructuralPattern", "get_structural_patterns"]

# Pre-compiled regexes used by the test functions.
_RE_NUMBERED_LINE = re.compile(r"^\s*\d+[\.\)]\s")
_RE_MD_HEADER = re.compile(r"^#{1,6}\s")
_RE_EMOJI = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f1e0-\U0001f1ff"  # flags
    "\U00002702-\U000027b0"
    "\U0001f900-\U0001f9ff"
    "\U0001fa00-\U0001fa6f"
    "\U0001fa70-\U0001faff"
    "]+",
    re.UNICODE,
)
_RE_BULLET_LINE = re.compile(r"^\s*[-*]\s+(.+)")
_RE_LEADING_VERB = re.compile(r"^([A-Z][a-z]+)\b")
_RE_SUMMARY_ENDING = re.compile(
    r"(?:in summary|in conclusion|to summarize|overall)[,.\s]",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class StructuralPattern:
    """A callable detection pattern that analyses text structure.

    Unlike regex-based patterns, structural patterns run arbitrary logic
    and return a float between 0.0 (no signal) and ``max_weight``.
    """

    name: str
    description: str
    max_weight: float
    test: Callable[[str], float]


# ---------------------------------------------------------------------------
# Individual test functions
# ---------------------------------------------------------------------------

def _numbered_list_heavy(text: str) -> float:
    """Detect text where the majority of lines are numbered items."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        return 0.0
    numbered = sum(1 for ln in lines if _RE_NUMBERED_LINE.match(ln))
    ratio = numbered / len(lines)
    return 0.3 if ratio > 0.5 else 0.0


def _header_heavy(text: str) -> float:
    """Detect excessive markdown headers relative to word count."""
    words = text.split()
    if len(words) >= 300:
        return 0.0
    header_count = sum(1 for ln in text.splitlines() if _RE_MD_HEADER.match(ln))
    return 0.25 if header_count >= 3 else 0.0


def _uniform_paragraph_length(text: str) -> float:
    """Detect suspiciously uniform paragraph lengths."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) < 4:
        return 0.0
    lengths = [len(p.split()) for p in paragraphs]
    mean = statistics.mean(lengths)
    if mean == 0:
        return 0.0
    stdev = statistics.pstdev(lengths)
    cv = stdev / mean
    return 0.3 if cv < 0.2 else 0.0


def _summary_conclusion(text: str) -> float:
    """Detect text ending with a summary/conclusion phrase."""
    # Check the last 200 characters.
    tail = text[-200:] if len(text) > 200 else text
    return 0.2 if _RE_SUMMARY_ENDING.search(tail) else 0.0


def _excessive_emoji(text: str) -> float:
    """Detect excessive emoji usage relative to word count."""
    emojis = _RE_EMOJI.findall(text)
    emoji_count = sum(len(e) for e in emojis)
    if emoji_count <= 5:
        return 0.0
    word_count = len(text.split())
    if word_count == 0:
        return 0.0
    ratio = emoji_count / word_count
    return 0.2 if ratio > 0.03 else 0.0


def _bullet_symmetry(text: str) -> float:
    """Detect bullet lists where most items begin with the same verb pattern."""
    bullet_texts: list[str] = []
    for ln in text.splitlines():
        m = _RE_BULLET_LINE.match(ln)
        if m:
            bullet_texts.append(m.group(1))
    if len(bullet_texts) < 4:
        return 0.0
    leading_verbs: list[str] = []
    for bt in bullet_texts:
        vm = _RE_LEADING_VERB.match(bt)
        if vm:
            leading_verbs.append(vm.group(1))
    if not leading_verbs:
        return 0.0
    most_common_count = max(leading_verbs.count(v) for v in set(leading_verbs))
    ratio = most_common_count / len(bullet_texts)
    return 0.25 if ratio > 0.7 else 0.0


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def get_structural_patterns() -> list[StructuralPattern]:
    """Return all built-in structural detection patterns."""
    return [
        StructuralPattern(
            name="numbered_list_heavy",
            description="More than 50% of lines are numbered items in text with 3+ lines",
            max_weight=0.3,
            test=_numbered_list_heavy,
        ),
        StructuralPattern(
            name="header_heavy",
            description="3+ markdown headers in fewer than 300 words",
            max_weight=0.25,
            test=_header_heavy,
        ),
        StructuralPattern(
            name="uniform_paragraph_length",
            description="Coefficient of variation < 0.2 across 4+ paragraphs",
            max_weight=0.3,
            test=_uniform_paragraph_length,
        ),
        StructuralPattern(
            name="summary_conclusion",
            description="Text ends with a summary/conclusion phrase",
            max_weight=0.2,
            test=_summary_conclusion,
        ),
        StructuralPattern(
            name="excessive_emoji",
            description="More than 5 emojis and emoji-to-word ratio above 0.03",
            max_weight=0.2,
            test=_excessive_emoji,
        ),
        StructuralPattern(
            name="bullet_symmetry",
            description="More than 70% of 4+ bullet points start with the same verb pattern",
            max_weight=0.25,
            test=_bullet_symmetry,
        ),
    ]
