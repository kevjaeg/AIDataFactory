"""Tests for the Inspector quality control stage (Stage 4)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pipeline.base import StageResult
from pipeline.quality_checks.toxicity import ToxicityChecker
from pipeline.quality_checks.readability import ReadabilityChecker
from pipeline.quality_checks.format_check import FormatChecker
from pipeline.quality_checks.duplicate_check import DuplicateChecker
from pipeline.stages.quality import InspectorStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_example(**overrides) -> dict:
    """Return a valid training example dict from the Factory stage."""
    base = {
        "input": "What is machine learning?",
        "output": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        "template_type": "qa",
        "model_used": "gpt-4o-mini",
        "token_count": 150,
        "cost": 0.001,
        "source_chunk": "Machine learning overview...",
        "source_url": "https://example.com/ml",
    }
    base.update(overrides)
    return base


def _bad_example_empty_input() -> dict:
    return _good_example(input="", output="A valid long enough output for testing purposes.")


def _bad_example_short_output() -> dict:
    return _good_example(output="Too short.")


# ---------------------------------------------------------------------------
# ToxicityChecker
# ---------------------------------------------------------------------------

class TestToxicityChecker:
    @patch("pipeline.quality_checks.toxicity.Detoxify")
    async def test_toxicity_checker_clean_text(self, mock_detoxify_cls):
        mock_model = MagicMock()
        mock_model.predict.return_value = {
            "toxicity": 0.01,
            "severe_toxicity": 0.0,
            "obscene": 0.0,
            "threat": 0.0,
            "insult": 0.0,
            "identity_attack": 0.0,
        }
        mock_detoxify_cls.return_value = mock_model

        checker = ToxicityChecker()
        example = _good_example()
        score, detail = await checker.check(example)

        assert score == pytest.approx(0.99, abs=0.02)
        assert "clean" in detail.lower() or score > 0.9

    @patch("pipeline.quality_checks.toxicity.Detoxify")
    async def test_toxicity_checker_toxic_text(self, mock_detoxify_cls):
        mock_model = MagicMock()
        mock_model.predict.return_value = {
            "toxicity": 0.95,
            "severe_toxicity": 0.8,
            "obscene": 0.9,
            "threat": 0.1,
            "insult": 0.85,
            "identity_attack": 0.3,
        }
        mock_detoxify_cls.return_value = mock_model

        checker = ToxicityChecker()
        example = _good_example()
        score, detail = await checker.check(example)

        assert score < 0.15
        assert score >= 0.0


# ---------------------------------------------------------------------------
# ReadabilityChecker
# ---------------------------------------------------------------------------

class TestReadabilityChecker:
    async def test_readability_checker_simple_text(self):
        checker = ReadabilityChecker()
        example = _good_example(
            output="The cat sat on the mat. The dog ran in the park. It was a sunny day."
        )
        score, detail = await checker.check(example)

        assert score > 0.6
        assert "Flesch" in detail

    async def test_readability_checker_complex_text(self):
        checker = ReadabilityChecker()
        example = _good_example(
            output=(
                "Notwithstanding the aforementioned epistemological considerations, "
                "the phenomenological manifestation of transcendental hermeneutics "
                "necessitates a paradigmatic reconceptualization of ontological presuppositions "
                "vis-a-vis the dialectical interplay between deconstructivist methodologies "
                "and poststructuralist interpretive frameworks."
            )
        )
        score, detail = await checker.check(example)

        # Complex academic text should have lower readability
        assert score < 0.5
        assert "Flesch" in detail


# ---------------------------------------------------------------------------
# FormatChecker
# ---------------------------------------------------------------------------

class TestFormatChecker:
    async def test_format_checker_valid_example(self):
        checker = FormatChecker()
        example = _good_example()
        score, detail = await checker.check(example)

        assert score == 1.0
        assert "valid" in detail.lower()

    async def test_format_checker_empty_input(self):
        checker = FormatChecker()
        example = _bad_example_empty_input()
        score, detail = await checker.check(example)

        assert score == 0.0
        assert "input" in detail.lower()

    async def test_format_checker_short_output(self):
        checker = FormatChecker()
        example = _bad_example_short_output()
        score, detail = await checker.check(example)

        assert score == 0.0
        assert "output" in detail.lower()


# ---------------------------------------------------------------------------
# DuplicateChecker
# ---------------------------------------------------------------------------

class TestDuplicateChecker:
    async def test_duplicate_checker_unique_examples(self):
        checker = DuplicateChecker()
        examples = [
            _good_example(input="What is Python?", output="Python is a programming language."),
            _good_example(input="What is Java?", output="Java is an object-oriented language."),
            _good_example(input="What is Rust?", output="Rust is a systems programming language."),
        ]
        checker.set_examples(examples)

        score, detail = await checker.check(examples[0], index=0)
        assert score == 1.0
        assert "unique" in detail.lower()

    async def test_duplicate_checker_detects_duplicates(self):
        checker = DuplicateChecker()
        examples = [
            _good_example(
                input="What is machine learning?",
                output="Machine learning is a subset of artificial intelligence.",
            ),
            _good_example(
                input="What is machine learning?",
                output="Machine learning is a subset of artificial intelligence.",
            ),
        ]
        checker.set_examples(examples)

        # Check the second example -- it should be marked as a duplicate
        score, detail = await checker.check(examples[1], index=1)
        assert score < 1.0
        assert "duplicate" in detail.lower() or "similar" in detail.lower()


# ---------------------------------------------------------------------------
# InspectorStage -- basic identity
# ---------------------------------------------------------------------------

class TestInspectorStageBasics:
    def test_inspector_stage_name(self):
        stage = InspectorStage()
        assert stage.stage_name == "inspector"

    async def test_inspector_validate_input(self):
        stage = InspectorStage()
        # Valid: non-empty list of dicts with input/output
        assert await stage.validate_input([_good_example()]) is True
        # Invalid: empty list
        assert await stage.validate_input([]) is False
        # Invalid: not a list
        assert await stage.validate_input("not a list") is False
        # Invalid: list of non-dicts
        assert await stage.validate_input(["not a dict"]) is False
        # Invalid: dict without required keys
        assert await stage.validate_input([{"foo": "bar"}]) is False


# ---------------------------------------------------------------------------
# InspectorStage -- process
# ---------------------------------------------------------------------------

class TestInspectorProcess:
    @patch("pipeline.quality_checks.toxicity.Detoxify")
    async def test_inspector_process_passes_good_examples(self, mock_detoxify_cls):
        """Good examples should pass QC with score above threshold."""
        mock_model = MagicMock()
        mock_model.predict.return_value = {
            "toxicity": 0.01,
            "severe_toxicity": 0.0,
            "obscene": 0.0,
            "threat": 0.0,
            "insult": 0.0,
            "identity_attack": 0.0,
        }
        mock_detoxify_cls.return_value = mock_model

        stage = InspectorStage()
        examples = [_good_example()]
        result = await stage.process(examples, config={"checks": ["toxicity", "readability", "format"]})

        assert isinstance(result, StageResult)
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["passed_qc"] is True

    @patch("pipeline.quality_checks.toxicity.Detoxify")
    async def test_inspector_process_fails_bad_examples(self, mock_detoxify_cls):
        """Examples with toxic content should fail QC."""
        mock_model = MagicMock()
        mock_model.predict.return_value = {
            "toxicity": 0.95,
            "severe_toxicity": 0.9,
            "obscene": 0.9,
            "threat": 0.5,
            "insult": 0.9,
            "identity_attack": 0.7,
        }
        mock_detoxify_cls.return_value = mock_model

        stage = InspectorStage()
        examples = [_good_example()]
        result = await stage.process(examples, config={"checks": ["toxicity", "readability", "format"]})

        assert isinstance(result, StageResult)
        assert result.success is True
        # Toxic content should pull the average score below threshold
        assert result.data[0]["quality_score"] < 0.7
        assert result.data[0]["passed_qc"] is False

    @patch("pipeline.quality_checks.toxicity.Detoxify")
    async def test_inspector_process_adds_quality_fields(self, mock_detoxify_cls):
        """Each example should be enriched with quality_score, quality_details, passed_qc."""
        mock_model = MagicMock()
        mock_model.predict.return_value = {
            "toxicity": 0.02,
            "severe_toxicity": 0.0,
            "obscene": 0.0,
            "threat": 0.0,
            "insult": 0.0,
            "identity_attack": 0.0,
        }
        mock_detoxify_cls.return_value = mock_model

        stage = InspectorStage()
        examples = [_good_example()]
        result = await stage.process(examples, config={"checks": ["toxicity", "readability", "format"]})

        example = result.data[0]
        # Original fields preserved
        assert example["input"] == "What is machine learning?"
        assert example["output"].startswith("Machine learning")
        assert example["template_type"] == "qa"
        # Quality fields added
        assert "quality_score" in example
        assert "quality_details" in example
        assert "passed_qc" in example
        assert isinstance(example["quality_score"], float)
        assert isinstance(example["quality_details"], dict)
        assert isinstance(example["passed_qc"], bool)
        # quality_details has per-checker entries
        assert "toxicity" in example["quality_details"]
        assert "readability" in example["quality_details"]
        assert "format" in example["quality_details"]
        for check_name, check_info in example["quality_details"].items():
            assert "score" in check_info
            assert "detail" in check_info

    @patch("pipeline.quality_checks.toxicity.Detoxify")
    async def test_inspector_stats_include_pass_fail_counts(self, mock_detoxify_cls):
        """Stats should include total, passed, and failed counts."""
        mock_model = MagicMock()
        # First call: clean, second call: toxic
        mock_model.predict.side_effect = [
            {
                "toxicity": 0.01, "severe_toxicity": 0.0, "obscene": 0.0,
                "threat": 0.0, "insult": 0.0, "identity_attack": 0.0,
            },
            {
                "toxicity": 0.99, "severe_toxicity": 0.9, "obscene": 0.9,
                "threat": 0.5, "insult": 0.9, "identity_attack": 0.7,
            },
        ]
        mock_detoxify_cls.return_value = mock_model

        stage = InspectorStage()
        examples = [
            _good_example(),
            _good_example(input="Some other question here", output="Another valid output that is long enough for testing."),
        ]
        result = await stage.process(examples, config={"checks": ["toxicity", "readability", "format"]})

        assert "total" in result.stats
        assert "passed" in result.stats
        assert "failed" in result.stats
        assert result.stats["total"] == 2
        assert result.stats["passed"] + result.stats["failed"] == result.stats["total"]
