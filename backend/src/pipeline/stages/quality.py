"""Inspector stage: run quality checks on training examples."""

from __future__ import annotations

from typing import Any

from loguru import logger

from pipeline.base import PipelineStage, StageResult
from pipeline.quality_checks import QualityChecker
from pipeline.quality_checks.toxicity import ToxicityChecker
from pipeline.quality_checks.readability import ReadabilityChecker
from pipeline.quality_checks.format_check import FormatChecker
from pipeline.quality_checks.duplicate_check import DuplicateChecker
from pipeline.quality_checks.coherence import CoherenceChecker
from pipeline.quality_checks.length_balance import LengthBalanceChecker


# Registry mapping config names to checker classes
_CHECKER_REGISTRY: dict[str, type[QualityChecker]] = {
    "toxicity": ToxicityChecker,
    "readability": ReadabilityChecker,
    "format": FormatChecker,
    "duplicate": DuplicateChecker,
    "coherence": CoherenceChecker,
    "length_balance": LengthBalanceChecker,
}


class InspectorStage(PipelineStage):
    """Stage 4 (Inspector): validate training examples against quality checks.

    For each example produced by the Factory stage, this stage:

    1. Runs all configured quality checkers.
    2. Computes an aggregate ``quality_score`` (weighted average of individual
       scores).
    3. Marks ``passed_qc`` based on the ``min_score`` threshold.
    4. Attaches a ``quality_details`` dict with per-checker results.

    Configuration keys (passed via *config* dict):

    * ``min_score`` -- minimum aggregate score to pass QC (default ``0.7``).
    * ``checks`` -- list of checker names to run (default
      ``["toxicity", "readability", "format"]``).
    * ``weights`` -- dict mapping checker name to weight (default ``1.0``
      for each checker).  Example: ``{"toxicity": 2.0, "readability": 1.0}``.
    """

    stage_name = "inspector"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_input(self, input_data: Any) -> bool:
        """Input must be a non-empty list of dicts with ``input`` and ``output``."""
        if not isinstance(input_data, list) or len(input_data) == 0:
            return False
        for item in input_data:
            if not isinstance(item, dict):
                return False
            if "input" not in item or "output" not in item:
                return False
        return True

    # ------------------------------------------------------------------
    # Main processing
    # ------------------------------------------------------------------

    async def process(self, input_data: list[dict], config: dict) -> StageResult:
        """Run quality checks on every example in *input_data*."""
        min_score: float = config.get("min_score", 0.7)
        check_names: list[str] = config.get(
            "checks", ["toxicity", "readability", "format"]
        )
        weights_cfg: dict[str, float] = config.get("weights", {})

        # Instantiate configured checkers
        checkers: list[QualityChecker] = []
        for name in check_names:
            cls = _CHECKER_REGISTRY.get(name)
            if cls is None:
                logger.warning(f"Unknown quality checker: {name!r}")
                continue
            checkers.append(cls())

        # Pre-populate duplicate checker with the full example list
        for checker in checkers:
            if isinstance(checker, DuplicateChecker):
                checker.set_examples(input_data)

        enriched: list[dict] = []
        errors: list[str] = []
        passed_count = 0
        failed_count = 0

        for idx, example in enumerate(input_data):
            quality_details: dict[str, dict[str, Any]] = {}
            weighted_scores: list[tuple[float, float]] = []

            for checker in checkers:
                weight = weights_cfg.get(checker.name, 1.0)
                try:
                    # Pass index to DuplicateChecker for reliable lookup
                    if isinstance(checker, DuplicateChecker):
                        score, detail = await checker.check(example, index=idx)
                    else:
                        score, detail = await checker.check(example)
                    quality_details[checker.name] = {
                        "score": score,
                        "detail": detail,
                    }
                    weighted_scores.append((score, weight))
                except Exception as exc:
                    logger.warning(
                        f"Checker {checker.name!r} failed on example: {exc}"
                    )
                    errors.append(f"{checker.name}: {exc}")
                    quality_details[checker.name] = {
                        "score": 0.0,
                        "detail": f"error: {exc}",
                    }
                    weighted_scores.append((0.0, weight))

            total_weight = sum(w for _, w in weighted_scores)
            quality_score = float(
                sum(s * w for s, w in weighted_scores) / total_weight
                if total_weight > 0
                else 0.0
            )
            passed_qc = bool(quality_score >= min_score)

            if passed_qc:
                passed_count += 1
            else:
                failed_count += 1

            # Build enriched example (preserving all original fields)
            enriched_example = {**example}
            enriched_example["quality_score"] = quality_score
            enriched_example["quality_details"] = quality_details
            enriched_example["passed_qc"] = passed_qc
            enriched.append(enriched_example)

        return StageResult(
            success=True,
            data=enriched,
            errors=errors,
            stats={
                "total": len(enriched),
                "passed": passed_count,
                "failed": failed_count,
                "checks_run": check_names,
                "min_score": min_score,
            },
        )
