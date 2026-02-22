"""Shipper stage: export QC-annotated training examples to various formats."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from pipeline.base import PipelineStage, StageResult


class ShipperStage(PipelineStage):
    """Stage 5 (Shipper): export training examples that passed QC.

    For each set of QC-annotated examples, this stage:

    1. Filters to only examples where ``passed_qc`` is True (or includes
       all examples if the key is absent).
    2. Formats into the target format: JSON, JSONL, or CSV.
    3. Generates a dataset card (Markdown) with statistics.
    4. Writes files to ``data/exports/{job_id}/{version}.{format}`` and
       ``data/exports/{job_id}/{version}_card.md``.

    Configuration keys (passed via *config* dict):

    * ``format`` -- export format: ``"json"``, ``"jsonl"``, or ``"csv"``
      (default ``"jsonl"``).
    * ``job_id`` -- job identifier (required).
    * ``version`` -- dataset version string (default ``"v1"``).
    * ``data_dir`` -- base data directory (default ``Path("data")``).
    """

    stage_name = "shipper"

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
        """Filter, format, and export training examples."""
        export_format: str = config.get("format", "jsonl").lower()
        job_id = config.get("job_id")
        version: str = config.get("version", "v1")
        data_dir: Path = Path(config.get("data_dir", "data"))

        if job_id is None:
            return StageResult(
                success=False,
                errors=["Missing required config key: job_id"],
            )

        if export_format not in ("json", "jsonl", "csv"):
            return StageResult(
                success=False,
                errors=[f"Unsupported export format: {export_format}"],
            )

        # --- Filter examples ---
        passed_examples: list[dict] = []
        filtered_out = 0
        for example in input_data:
            if "passed_qc" not in example or example["passed_qc"]:
                passed_examples.append(example)
            else:
                filtered_out += 1

        # --- Format output ---
        formatted = self._format_examples(passed_examples, export_format)

        # --- Generate dataset card ---
        dataset_card = self._generate_dataset_card(
            job_id=job_id,
            version=version,
            export_format=export_format,
            total=len(input_data),
            passed=len(passed_examples),
            filtered=filtered_out,
            examples=input_data,
        )

        # --- Write files ---
        export_dir = data_dir / "exports" / str(job_id)
        export_dir.mkdir(parents=True, exist_ok=True)

        file_path = export_dir / f"{version}.{export_format}"
        card_path = export_dir / f"{version}_card.md"

        file_path.write_text(formatted, encoding="utf-8")
        card_path.write_text(dataset_card, encoding="utf-8")

        logger.info(
            f"Exported {len(passed_examples)} examples to {file_path} "
            f"({filtered_out} filtered out)"
        )

        return StageResult(
            success=True,
            data=passed_examples,
            errors=[],
            stats={
                "file_path": str(file_path),
                "record_count": len(passed_examples),
                "dataset_card_path": str(card_path),
                "format": export_format,
                "total_filtered_out": filtered_out,
            },
        )

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_examples(
        self, examples: list[dict], export_format: str
    ) -> str:
        """Format passed examples into the target format string."""
        # Extract only input/output fields
        records = [{"input": ex["input"], "output": ex["output"]} for ex in examples]

        if export_format == "json":
            return json.dumps(records, indent=2, ensure_ascii=False)

        if export_format == "jsonl":
            lines = [json.dumps(r, ensure_ascii=False) for r in records]
            return "\n".join(lines) + ("\n" if lines else "")

        # csv
        buf = io.StringIO(newline="")
        writer = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(["input", "output"])
        for r in records:
            writer.writerow([r["input"], r["output"]])
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Dataset card
    # ------------------------------------------------------------------

    def _generate_dataset_card(
        self,
        *,
        job_id: int | str,
        version: str,
        export_format: str,
        total: int,
        passed: int,
        filtered: int,
        examples: list[dict],
    ) -> str:
        """Generate a Markdown dataset card with statistics."""
        # Quality score distribution
        scores = [
            ex.get("quality_score", 0.0)
            for ex in examples
            if "quality_score" in ex
        ]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        excellent = sum(1 for s in scores if s >= 0.9)
        good = sum(1 for s in scores if 0.7 <= s < 0.9)
        fair = sum(1 for s in scores if 0.5 <= s < 0.7)
        poor = sum(1 for s in scores if s < 0.5)

        export_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return f"""# Dataset Card

## Overview
- **Job ID**: {job_id}
- **Version**: {version}
- **Format**: {export_format}
- **Export Date**: {export_date}

## Statistics
- **Total examples**: {total}
- **Passed QC**: {passed}
- **Filtered out**: {filtered}
- **Average quality score**: {avg_score:.3f}

## Quality Score Distribution
- Excellent (>= 0.9): {excellent}
- Good (>= 0.7): {good}
- Fair (>= 0.5): {fair}
- Poor (< 0.5): {poor}

## Fields
- `input`: The input prompt or question
- `output`: The expected response or answer
"""
