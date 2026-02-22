"""Duplicate quality checker using word-overlap cosine similarity."""

from __future__ import annotations

import math
from collections import Counter

from pipeline.quality_checks import QualityChecker


def _word_vector(text: str) -> Counter:
    """Build a simple word-frequency (TF) vector from *text*."""
    return Counter(text.lower().split())


def _cosine_similarity(a: Counter, b: Counter) -> float:
    """Compute cosine similarity between two Counter-based word vectors."""
    if not a or not b:
        return 0.0

    common_keys = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in common_keys)

    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


class DuplicateChecker(QualityChecker):
    """Detects near-duplicate training examples via word-overlap cosine similarity.

    Call :meth:`set_examples` with the full list of examples **before**
    calling :meth:`check` so the checker can compare each example against
    the others.

    Examples with cosine similarity >= ``threshold`` (default 0.9) against
    any *earlier* example in the list are considered duplicates and receive
    a lower score.
    """

    name = "duplicate"

    def __init__(self, threshold: float = 0.9) -> None:
        self._threshold = threshold
        self._examples: list[dict] = []
        self._vectors: list[Counter] = []

    def set_examples(self, examples: list[dict]) -> None:
        """Pre-compute word vectors for the full example set."""
        self._examples = examples
        self._vectors = [
            _word_vector(f"{ex.get('input', '')} {ex.get('output', '')}")
            for ex in examples
        ]

    async def check(
        self, example: dict, *, index: int | None = None
    ) -> tuple[float, str]:
        text = f"{example.get('input', '')} {example.get('output', '')}"
        vec = _word_vector(text)

        max_sim = 0.0
        # Compare only against earlier examples to avoid double-flagging
        compare_range = range(index) if index is not None else range(len(self._vectors))
        for i in compare_range:
            sim = _cosine_similarity(vec, self._vectors[i])
            max_sim = max(max_sim, sim)

        if max_sim >= self._threshold:
            score = 1.0 - max_sim
            return score, f"duplicate detected (similarity: {max_sim:.3f})"

        return 1.0, "unique"
