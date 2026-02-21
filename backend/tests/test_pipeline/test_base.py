import pytest
from dataclasses import fields

from pipeline.base import PipelineStage, StageResult


def test_stage_result_defaults() -> None:
    result = StageResult(success=True)
    assert result.success is True
    assert result.data == []
    assert result.errors == []
    assert result.stats == {}


def test_stage_result_with_data() -> None:
    result = StageResult(
        success=True,
        data=[{"url": "https://example.com", "html": "<h1>Test</h1>"}],
        stats={"documents_scraped": 1, "total_bytes": 1024},
    )
    assert len(result.data) == 1
    assert result.stats["documents_scraped"] == 1


def test_stage_result_failure() -> None:
    result = StageResult(
        success=False,
        errors=["Connection timeout for https://example.com"],
        stats={"attempted": 1, "failed": 1},
    )
    assert result.success is False
    assert len(result.errors) == 1


class MockStage(PipelineStage):
    """A minimal mock stage to verify the abstract base class works."""
    stage_name = "mock"

    async def process(self, input_data, config: dict) -> StageResult:
        return StageResult(success=True, data=input_data)

    async def validate_input(self, input_data) -> bool:
        return isinstance(input_data, list)


async def test_pipeline_stage_can_be_subclassed() -> None:
    stage = MockStage()
    assert stage.stage_name == "mock"
    result = await stage.process(["item1", "item2"], config={})
    assert result.success is True
    assert result.data == ["item1", "item2"]


async def test_pipeline_stage_validate_input() -> None:
    stage = MockStage()
    assert await stage.validate_input(["valid"]) is True
    assert await stage.validate_input("invalid") is False


def test_pipeline_stage_is_abstract() -> None:
    """Cannot instantiate PipelineStage directly."""
    with pytest.raises(TypeError):
        PipelineStage()
