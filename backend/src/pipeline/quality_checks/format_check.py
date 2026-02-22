"""Format quality checker for training example structure validation."""

from __future__ import annotations

from pipeline.quality_checks import QualityChecker


class FormatChecker(QualityChecker):
    """Validates the structural format of a training example.

    Checks:
    * ``input`` and ``output`` fields exist and are non-empty strings.
    * ``input`` length >= 10 characters.
    * ``output`` length >= 20 characters.
    * Neither field is whitespace-only.
    """

    name = "format"

    async def check(self, example: dict) -> tuple[float, str]:
        input_text = example.get("input", "")
        output_text = example.get("output", "")

        # Must be strings
        if not isinstance(input_text, str) or not isinstance(output_text, str):
            return 0.0, "input and output must be strings"

        # Must not be whitespace-only
        if not input_text.strip():
            return 0.0, "input is empty or whitespace-only"

        if not output_text.strip():
            return 0.0, "output is empty or whitespace-only"

        # Minimum length checks
        if len(input_text.strip()) < 10:
            return 0.0, f"input too short ({len(input_text.strip())} chars, need >= 10)"

        if len(output_text.strip()) < 20:
            return 0.0, f"output too short ({len(output_text.strip())} chars, need >= 20)"

        return 1.0, "valid format"
