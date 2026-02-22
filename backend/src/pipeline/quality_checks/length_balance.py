"""Length balance quality checker — compares input/output word counts."""

from __future__ import annotations

from pipeline.quality_checks import QualityChecker


class LengthBalanceChecker(QualityChecker):
    """Checks that the output length is reasonable relative to the input.

    Ideal ratio range: 0.5x to 20x (output words / input words).
    Score degrades smoothly outside this range.
    No external dependencies required.
    """

    name = "length_balance"

    async def check(self, example: dict) -> tuple[float, str]:
        input_text = example.get("input", "").strip()
        output_text = example.get("output", "").strip()

        input_words = len(input_text.split()) if input_text else 0
        output_words = len(output_text.split()) if output_text else 0

        if input_words == 0 and output_words == 0:
            return 0.5, "both input and output are empty"
        if input_words == 0:
            return 0.3, f"empty input, output has {output_words} words"
        if output_words == 0:
            return 0.0, "empty output"

        ratio = output_words / input_words

        # Ideal range: 0.5x - 20x
        if 0.5 <= ratio <= 20.0:
            score = 1.0
            detail = f"balanced (ratio: {ratio:.1f}x, {input_words}→{output_words} words)"
        elif ratio < 0.5:
            # Output too short: score degrades linearly from 1.0 at 0.5 to 0.0 at 0.0
            score = max(0.0, ratio / 0.5)
            detail = f"output too short (ratio: {ratio:.2f}x, {input_words}→{output_words} words)"
        else:
            # Output too long: score degrades from 1.0 at 20x to 0.0 at 100x
            score = max(0.0, 1.0 - (ratio - 20.0) / 80.0)
            detail = f"output too long (ratio: {ratio:.1f}x, {input_words}→{output_words} words)"

        return score, detail
