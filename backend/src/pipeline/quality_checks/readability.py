"""Readability quality checker using the textstat library."""

from __future__ import annotations

import textstat

from pipeline.quality_checks import QualityChecker


class ReadabilityChecker(QualityChecker):
    """Scores text readability using the Flesch Reading Ease metric.

    Flesch scores range from 0 to 100+ (higher = more readable).  We
    normalise to the 0--1 range by dividing by 100 and clamping.
    """

    name = "readability"

    async def check(self, example: dict) -> tuple[float, str]:
        text = example.get("output", "")

        if not text or not text.strip():
            return 0.0, "no output text to evaluate"

        flesch = textstat.flesch_reading_ease(text)
        score = min(max(flesch / 100.0, 0.0), 1.0)
        detail = f"Flesch: {flesch:.1f}"

        return score, detail
