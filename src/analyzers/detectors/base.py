"""Base detector with shared text analysis utilities."""

from abc import ABC

from src.domain.entities import Signal
from src.domain.interfaces import IDetector

__all__ = ["BaseDetector"]


class BaseDetector(IDetector, ABC):
    """Provides common text analysis utilities for all detectors."""

    @staticmethod
    def word_count(text: str) -> int:
        """Count the number of whitespace-delimited words in *text*."""
        return len(text.split())

    @staticmethod
    def line_count(text: str) -> int:
        """Count the number of non-blank lines in *text*."""
        return len([line for line in text.split("\n") if line.strip()])

    @staticmethod
    def paragraph_count(text: str) -> int:
        """Count the number of non-blank paragraphs (separated by blank lines)."""
        return len([p for p in text.split("\n\n") if p.strip()])
