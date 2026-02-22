"""Quality checkers for training data validation."""

from __future__ import annotations

from abc import ABC, abstractmethod


class QualityChecker(ABC):
    """Base class for all quality checkers.

    Each checker evaluates a single training example and returns a score
    between 0.0 (worst) and 1.0 (best) along with a human-readable detail
    message.
    """

    name: str

    @abstractmethod
    async def check(self, example: dict) -> tuple[float, str]:
        """Check a single example.

        Returns:
            A tuple of ``(score, detail_message)`` where *score* is in the
            range 0.0--1.0 and *detail_message* explains the result.
        """
        ...
