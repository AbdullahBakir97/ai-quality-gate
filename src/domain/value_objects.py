"""Immutable value objects for the AI Quality Gate domain."""

from dataclasses import dataclass

__all__ = [
    "Score",
    "Threshold",
]


@dataclass(frozen=True, slots=True)
class Score:
    """Normalized score clamped to the 0-100 range."""

    value: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", max(0, min(100, self.value)))


@dataclass(frozen=True, slots=True)
class Threshold:
    """Warning and failure thresholds with warn < fail invariant."""

    warn: int
    fail: int

    def __post_init__(self) -> None:
        if self.warn >= self.fail:
            raise ValueError(
                f"warn ({self.warn}) must be less than fail ({self.fail})"
            )
