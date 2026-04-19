"""Tests for the signal aggregator."""

import pytest

from src.analyzers.aggregator import SignalAggregator
from src.domain.entities import Signal
from src.domain.enums import Confidence, SignalType


@pytest.fixture
def aggregator() -> SignalAggregator:
    return SignalAggregator()


def _make_signal(weight: float = 0.3, occurrences: int = 1) -> Signal:
    return Signal(
        type=SignalType.AI_VOCABULARY,
        pattern="test",
        description="test signal",
        weight=weight,
        occurrences=occurrences,
    )


class TestSignalAggregator:
    """Tests for signal aggregation into AI score and confidence."""

    def test_no_signals_returns_zero(self, aggregator: SignalAggregator):
        score, confidence, is_ai = aggregator.aggregate([], "some text")
        assert score == 0
        assert confidence == Confidence.NONE
        assert is_ai is False

    def test_high_signals_produce_high_score(self, aggregator: SignalAggregator):
        signals = [_make_signal(0.4) for _ in range(8)]
        score, confidence, is_ai = aggregator.aggregate(signals, "")
        assert score >= 70
        assert confidence == Confidence.HIGH
        assert is_ai is True

    def test_few_signals_produce_low_confidence(self, aggregator: SignalAggregator):
        signals = [_make_signal(0.2)]
        _score, confidence, _is_ai = aggregator.aggregate(signals, "")
        assert confidence in (Confidence.MINIMAL, Confidence.NONE)

    def test_score_capped_at_100(self, aggregator: SignalAggregator):
        signals = [_make_signal(0.5, 3) for _ in range(20)]
        score, _, _ = aggregator.aggregate(signals, "")
        assert score <= 100

    def test_medium_confidence_threshold(self, aggregator: SignalAggregator):
        signals = [_make_signal(0.3) for _ in range(4)]
        _score, confidence, _ = aggregator.aggregate(signals, "")
        assert confidence in (Confidence.MEDIUM, Confidence.LOW)
