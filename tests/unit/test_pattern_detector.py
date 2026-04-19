"""Tests for the pattern-based AI detector."""

import pytest

from src.analyzers.detectors.pattern_detector import PatternDetector
from src.analyzers.patterns.registry import PatternRegistry
from src.analyzers.patterns import register_default_patterns
from src.domain.enums import SignalType


@pytest.fixture
def detector(pattern_registry: PatternRegistry) -> PatternDetector:
    return PatternDetector(pattern_registry)


class TestPatternDetector:
    """Tests for AI vocabulary and phrasing detection."""

    async def test_detects_ai_vocabulary(self, detector: PatternDetector):
        text = "This solution delves into the holistic approach to leverage robust patterns."
        signals = await detector.detect(text)
        assert len(signals) > 0
        vocab_signals = [s for s in signals if s.type == SignalType.AI_VOCABULARY]
        assert len(vocab_signals) >= 3  # delve, holistic, leverage, robust

    async def test_detects_ai_phrasing(self, detector: PatternDetector):
        text = "I'd be happy to help. Hope this helps! Here's a breakdown of the changes."
        signals = await detector.detect(text)
        phrasing_signals = [s for s in signals if s.type == SignalType.AI_PHRASING]
        assert len(phrasing_signals) >= 3

    async def test_no_false_positives_on_human_text(self, detector: PatternDetector, human_written_text: str):
        signals = await detector.detect(human_written_text)
        total_weight = sum(s.contribution for s in signals)
        assert total_weight < 1.0  # Very low signal weight for human text

    async def test_high_signal_on_ai_text(self, detector: PatternDetector, ai_generated_text: str):
        signals = await detector.detect(ai_generated_text)
        assert len(signals) >= 8
        total_weight = sum(s.contribution for s in signals)
        assert total_weight > 2.0

    async def test_empty_text_returns_no_signals(self, detector: PatternDetector):
        signals = await detector.detect("")
        assert signals == []

    async def test_signal_occurrences_counted(self, detector: PatternDetector):
        text = "We should leverage this and leverage that, leveraging everything."
        signals = await detector.detect(text)
        leverage_signal = next((s for s in signals if "leverage" in s.pattern.lower()), None)
        assert leverage_signal is not None
        assert leverage_signal.occurrences >= 2


class TestPatternRegistry:
    """Tests for the pattern registry."""

    def test_default_patterns_registered(self, pattern_registry: PatternRegistry):
        assert pattern_registry.count > 30

    def test_vocabulary_patterns_present(self, pattern_registry: PatternRegistry):
        vocab = pattern_registry.get_by_type(SignalType.AI_VOCABULARY)
        assert len(vocab) >= 20

    def test_phrasing_patterns_present(self, pattern_registry: PatternRegistry):
        phrasing = pattern_registry.get_by_type(SignalType.AI_PHRASING)
        assert len(phrasing) >= 10

    def test_clear_removes_all(self, pattern_registry: PatternRegistry):
        pattern_registry.clear()
        assert pattern_registry.count == 0
