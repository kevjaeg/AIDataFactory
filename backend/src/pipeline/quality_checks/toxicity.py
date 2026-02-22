"""Toxicity quality checker using the detoxify library."""

from __future__ import annotations

from detoxify import Detoxify

from pipeline.quality_checks import QualityChecker


class ToxicityChecker(QualityChecker):
    """Scores text toxicity using the ``detoxify`` model.

    The detoxify model returns toxicity probabilities in the range 0 (clean)
    to 1 (toxic).  We **invert** the maximum score so that our quality score
    is 1.0 for clean text and 0.0 for very toxic text.
    """

    name = "toxicity"

    def __init__(self) -> None:
        self._model = Detoxify("original")

    async def check(self, example: dict) -> tuple[float, str]:
        input_text = example.get("input", "")
        output_text = example.get("output", "")
        combined = f"{input_text} {output_text}".strip()

        if not combined:
            return 1.0, "no text to check"

        results = self._model.predict(combined)
        max_toxicity = max(results.values())
        score = 1.0 - max_toxicity

        if score >= 0.9:
            detail = "clean"
        elif score >= 0.7:
            detail = f"mildly toxic (max toxicity: {max_toxicity:.3f})"
        else:
            detail = f"toxic (max toxicity: {max_toxicity:.3f})"

        return score, detail
