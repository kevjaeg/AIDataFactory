"""Tests for the Shipper export stage (Stage 5)."""

from __future__ import annotations

import csv
import io
import json

import pytest
from httpx import AsyncClient

from pipeline.base import StageResult
from pipeline.stages.export import ShipperStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _qc_example(*, passed: bool = True, score: float = 0.85, **overrides) -> dict:
    """Return a QC-annotated training example dict."""
    base = {
        "input": "What is machine learning?",
        "output": "Machine learning is a subset of artificial intelligence.",
        "template_type": "qa",
        "model_used": "gpt-4o-mini",
        "token_count": 150,
        "cost": 0.001,
        "source_chunk": "ML overview...",
        "source_url": "https://example.com/ml",
        "quality_score": score,
        "passed_qc": passed,
        "quality_details": {"toxicity": {"score": 0.99}, "readability": {"score": 0.8}},
    }
    base.update(overrides)
    return base


def _sample_examples() -> list[dict]:
    """Return a mixed list of passed/failed examples."""
    return [
        _qc_example(passed=True, score=0.95, input="Q1", output="A1"),
        _qc_example(passed=True, score=0.80, input="Q2", output="A2"),
        _qc_example(passed=False, score=0.40, input="Q3", output="A3"),
        _qc_example(passed=True, score=0.72, input="Q4", output="A4"),
        _qc_example(passed=False, score=0.30, input="Q5", output="A5"),
    ]


# ---------------------------------------------------------------------------
# ShipperStage -- basic identity
# ---------------------------------------------------------------------------

class TestShipperStageBasics:
    def test_shipper_stage_name(self):
        stage = ShipperStage()
        assert stage.stage_name == "shipper"

    async def test_validate_input_valid(self):
        stage = ShipperStage()
        data = [_qc_example()]
        assert await stage.validate_input(data) is True

    async def test_validate_input_multiple(self):
        stage = ShipperStage()
        data = [_qc_example(), _qc_example(input="Another Q", output="Another A")]
        assert await stage.validate_input(data) is True

    async def test_validate_input_invalid_empty_list(self):
        stage = ShipperStage()
        assert await stage.validate_input([]) is False

    async def test_validate_input_invalid_not_a_list(self):
        stage = ShipperStage()
        assert await stage.validate_input("not a list") is False

    async def test_validate_input_invalid_non_dict_items(self):
        stage = ShipperStage()
        assert await stage.validate_input(["not a dict"]) is False

    async def test_validate_input_invalid_missing_keys(self):
        stage = ShipperStage()
        assert await stage.validate_input([{"foo": "bar"}]) is False

    async def test_validate_input_invalid_missing_output(self):
        stage = ShipperStage()
        assert await stage.validate_input([{"input": "Q"}]) is False


# ---------------------------------------------------------------------------
# ShipperStage -- process: filtering
# ---------------------------------------------------------------------------

class TestShipperFiltering:
    async def test_process_filters_passed_qc(self, tmp_path):
        """Only examples with passed_qc=True should be in the output."""
        stage = ShipperStage()
        examples = _sample_examples()  # 3 passed, 2 failed
        config = {"job_id": 1, "version": "v1", "format": "jsonl", "data_dir": str(tmp_path)}

        result = await stage.process(examples, config)

        assert result.success is True
        assert len(result.data) == 3
        assert result.stats["record_count"] == 3
        assert result.stats["total_filtered_out"] == 2

    async def test_process_includes_all_when_no_qc(self, tmp_path):
        """Examples without passed_qc key should be included."""
        stage = ShipperStage()
        examples = [
            {"input": "Q1", "output": "A1"},
            {"input": "Q2", "output": "A2"},
            {"input": "Q3", "output": "A3"},
        ]
        config = {"job_id": 2, "version": "v1", "format": "jsonl", "data_dir": str(tmp_path)}

        result = await stage.process(examples, config)

        assert result.success is True
        assert len(result.data) == 3
        assert result.stats["total_filtered_out"] == 0


# ---------------------------------------------------------------------------
# ShipperStage -- process: format output
# ---------------------------------------------------------------------------

class TestShipperFormats:
    async def test_process_jsonl_format(self, tmp_path):
        """JSONL output should have one JSON object per line."""
        stage = ShipperStage()
        examples = [
            _qc_example(passed=True, input="Q1", output="A1"),
            _qc_example(passed=True, input="Q2", output="A2"),
        ]
        config = {"job_id": 10, "version": "v1", "format": "jsonl", "data_dir": str(tmp_path)}

        result = await stage.process(examples, config)

        file_path = tmp_path / "exports" / "10" / "v1.jsonl"
        assert file_path.exists()

        lines = file_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            obj = json.loads(line)
            assert "input" in obj
            assert "output" in obj

    async def test_process_json_format(self, tmp_path):
        """JSON output should be a valid JSON array."""
        stage = ShipperStage()
        examples = [
            _qc_example(passed=True, input="Q1", output="A1"),
            _qc_example(passed=True, input="Q2", output="A2"),
        ]
        config = {"job_id": 11, "version": "v1", "format": "json", "data_dir": str(tmp_path)}

        result = await stage.process(examples, config)

        file_path = tmp_path / "exports" / "11" / "v1.json"
        assert file_path.exists()

        data = json.loads(file_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["input"] == "Q1"
        assert data[1]["output"] == "A2"

    async def test_process_csv_format(self, tmp_path):
        """CSV output should have header + data rows."""
        stage = ShipperStage()
        examples = [
            _qc_example(passed=True, input="Q1", output="A1"),
            _qc_example(passed=True, input="Q2", output="A2"),
        ]
        config = {"job_id": 12, "version": "v1", "format": "csv", "data_dir": str(tmp_path)}

        result = await stage.process(examples, config)

        file_path = tmp_path / "exports" / "12" / "v1.csv"
        assert file_path.exists()

        content = file_path.read_text(encoding="utf-8")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        assert rows[0] == ["input", "output"]
        assert len(rows) == 3  # header + 2 data rows
        assert rows[1][0] == "Q1"
        assert rows[2][1] == "A2"


# ---------------------------------------------------------------------------
# ShipperStage -- process: dataset card
# ---------------------------------------------------------------------------

class TestShipperDatasetCard:
    async def test_process_generates_dataset_card(self, tmp_path):
        """Dataset card should contain key statistics."""
        stage = ShipperStage()
        examples = _sample_examples()
        config = {"job_id": 20, "version": "v1", "format": "jsonl", "data_dir": str(tmp_path)}

        result = await stage.process(examples, config)

        card_path = tmp_path / "exports" / "20" / "v1_card.md"
        assert card_path.exists()

        card = card_path.read_text(encoding="utf-8")
        assert "# Dataset Card" in card
        assert "Job ID" in card
        assert "20" in card
        assert "Total examples" in card
        assert "5" in card  # total
        assert "Passed QC" in card
        assert "3" in card  # passed
        assert "Filtered out" in card
        assert "2" in card  # filtered
        assert "Average quality score" in card
        assert "Quality Score Distribution" in card
        assert "Excellent" in card
        assert "Good" in card
        assert "Fair" in card
        assert "Poor" in card


# ---------------------------------------------------------------------------
# ShipperStage -- process: file creation and stats
# ---------------------------------------------------------------------------

class TestShipperOutputFiles:
    async def test_process_creates_output_files(self, tmp_path):
        """Both data file and card file must be created."""
        stage = ShipperStage()
        examples = [_qc_example(passed=True, input="Q1", output="A1")]
        config = {"job_id": 30, "version": "v2", "format": "jsonl", "data_dir": str(tmp_path)}

        result = await stage.process(examples, config)

        data_file = tmp_path / "exports" / "30" / "v2.jsonl"
        card_file = tmp_path / "exports" / "30" / "v2_card.md"
        assert data_file.exists()
        assert card_file.exists()

    async def test_process_stats(self, tmp_path):
        """StageResult.stats must have all expected keys."""
        stage = ShipperStage()
        examples = _sample_examples()
        config = {"job_id": 31, "version": "v1", "format": "jsonl", "data_dir": str(tmp_path)}

        result = await stage.process(examples, config)

        assert isinstance(result, StageResult)
        assert result.success is True
        assert "file_path" in result.stats
        assert "record_count" in result.stats
        assert "dataset_card_path" in result.stats
        assert "format" in result.stats
        assert "total_filtered_out" in result.stats
        assert result.stats["format"] == "jsonl"
        assert result.stats["record_count"] == 3
        assert result.stats["total_filtered_out"] == 2

    async def test_process_missing_job_id(self, tmp_path):
        """Missing job_id in config should fail gracefully."""
        stage = ShipperStage()
        examples = [_qc_example()]
        config = {"format": "jsonl", "data_dir": str(tmp_path)}

        result = await stage.process(examples, config)

        assert result.success is False
        assert len(result.errors) > 0

    async def test_process_unsupported_format(self, tmp_path):
        """Unsupported format should fail gracefully."""
        stage = ShipperStage()
        examples = [_qc_example()]
        config = {"job_id": 99, "format": "xml", "data_dir": str(tmp_path)}

        result = await stage.process(examples, config)

        assert result.success is False
        assert "xml" in result.errors[0].lower()


# ---------------------------------------------------------------------------
# Export API routes
# ---------------------------------------------------------------------------

class TestExportRoutes:
    async def test_list_exports_route(self, client: AsyncClient, tmp_path):
        """GET /api/jobs/{job_id}/exports should return list of exports."""
        # No exports yet — should return empty list
        response = await client.get("/api/jobs/1/exports")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_exports_with_data(self, client: AsyncClient, session_factory):
        """GET /api/jobs/{job_id}/exports returns exports when they exist."""
        from db.models import Export

        async with session_factory() as session:
            export = Export(
                job_id=1,
                format="jsonl",
                file_path="/tmp/fake/v1.jsonl",
                record_count=10,
                version="v1",
                dataset_card="# Card",
            )
            session.add(export)
            await session.commit()
            await session.refresh(export)

        response = await client.get("/api/jobs/1/exports")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["job_id"] == 1
        assert data[0]["format"] == "jsonl"
        assert data[0]["record_count"] == 10
        assert data[0]["version"] == "v1"

    async def test_download_export_route(self, client: AsyncClient, session_factory, tmp_path):
        """GET /api/exports/{id}/download should return the file."""
        from db.models import Export

        # Create a real file on disk
        export_file = tmp_path / "test_export.jsonl"
        export_file.write_text('{"input": "Q", "output": "A"}\n', encoding="utf-8")

        async with session_factory() as session:
            export = Export(
                job_id=1,
                format="jsonl",
                file_path=str(export_file),
                record_count=1,
                version="v1",
                dataset_card="# Card",
            )
            session.add(export)
            await session.commit()
            await session.refresh(export)
            export_id = export.id

        response = await client.get(f"/api/exports/{export_id}/download")
        assert response.status_code == 200
        assert "Q" in response.text

    async def test_download_export_not_found(self, client: AsyncClient):
        """GET /api/exports/{id}/download with bad ID should 404."""
        response = await client.get("/api/exports/99999/download")
        assert response.status_code == 404

    async def test_get_dataset_card_route(self, client: AsyncClient, session_factory):
        """GET /api/exports/{id}/card should return markdown text."""
        from db.models import Export

        card_text = "# Dataset Card\n\n## Overview\n- **Job ID**: 1"

        async with session_factory() as session:
            export = Export(
                job_id=1,
                format="jsonl",
                file_path="/tmp/fake/v1.jsonl",
                record_count=5,
                version="v1",
                dataset_card=card_text,
            )
            session.add(export)
            await session.commit()
            await session.refresh(export)
            export_id = export.id

        response = await client.get(f"/api/exports/{export_id}/card")
        assert response.status_code == 200
        assert "Dataset Card" in response.text
        assert "Job ID" in response.text

    async def test_get_dataset_card_not_found(self, client: AsyncClient):
        """GET /api/exports/{id}/card with bad ID should 404."""
        response = await client.get("/api/exports/99999/card")
        assert response.status_code == 404

    async def test_get_dataset_card_no_card(self, client: AsyncClient, session_factory):
        """GET /api/exports/{id}/card with no card text should 404."""
        from db.models import Export

        async with session_factory() as session:
            export = Export(
                job_id=1,
                format="jsonl",
                file_path="/tmp/fake/v1.jsonl",
                record_count=5,
                version="v1",
                dataset_card=None,
            )
            session.add(export)
            await session.commit()
            await session.refresh(export)
            export_id = export.id

        response = await client.get(f"/api/exports/{export_id}/card")
        assert response.status_code == 404
