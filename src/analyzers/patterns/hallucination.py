"""Hallucination detection patterns for identifying fabricated references."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from src.analyzers.patterns.structural import StructuralPattern

__all__ = ["get_hallucination_patterns"]

# Pre-compiled regexes for hallucination detection.
_RE_LONG_METHOD = re.compile(r"\b[a-z][a-zA-Z]{15,}\(")
_RE_SPECIFIC_VERSION = re.compile(r"\b\d+\.\d+\.\d+(?:\.\d+)?\b")
_RE_SEE_DOCS = re.compile(
    r"\bsee (?:the )?documentation\b", re.IGNORECASE
)
_RE_URL = re.compile(r"https?://\S+")


def _nonexistent_api_refs(text: str) -> float:
    """Detect references to very specific API methods that likely don't exist.

    Methods with names longer than 15 characters are flagged because
    AI models tend to hallucinate plausible-sounding but nonexistent
    API method names.
    """
    matches = _RE_LONG_METHOD.findall(text)
    return 0.3 if len(matches) >= 2 else 0.0


def _version_hallucination(text: str) -> float:
    """Detect suspiciously many specific version numbers in descriptive text.

    AI models often fabricate precise version numbers (e.g. 4.2.17)
    when they don't actually know the correct version.
    """
    versions = _RE_SPECIFIC_VERSION.findall(text)
    return 0.15 if len(versions) > 3 else 0.0


def _fake_references(text: str) -> float:
    """Detect mentions of documentation without actual URLs.

    AI models frequently say 'see the documentation' without linking
    to anything, suggesting a hallucinated reference.
    """
    doc_mentions = _RE_SEE_DOCS.findall(text)
    if not doc_mentions:
        return 0.0
    urls = _RE_URL.findall(text)
    # If there are doc references but no URLs nearby, it's suspicious.
    return 0.2 if len(doc_mentions) > len(urls) else 0.0


def get_hallucination_patterns() -> list[StructuralPattern]:
    """Return all built-in hallucination detection patterns."""
    return [
        StructuralPattern(
            name="nonexistent_api_refs",
            description="References very specific API methods (>15 chars) that likely don't exist",
            max_weight=0.3,
            test=_nonexistent_api_refs,
        ),
        StructuralPattern(
            name="version_hallucination",
            description="More than 3 very specific version numbers in descriptive text",
            max_weight=0.15,
            test=_version_hallucination,
        ),
        StructuralPattern(
            name="fake_references",
            description="Mentions 'see the documentation' without providing actual URLs",
            max_weight=0.2,
            test=_fake_references,
        ),
    ]
