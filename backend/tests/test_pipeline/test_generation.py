"""Tests for the Factory generation stage (Stage 3)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from clients.llm_client import LLMResponse
from pipeline.base import StageResult
from pipeline.stages.generation import FactoryStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_llm_client(
    response_content: str = '[{"input":"Q","output":"A"}]',
    model: str = "gpt-4o-mini",
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
    total_tokens: int = 150,
    cost: float = 0.001,
) -> MagicMock:
    """Return a mock LLMClient whose ``complete`` returns a canned LLMResponse."""
    client = MagicMock()
    client.complete = AsyncMock(
        return_value=LLMResponse(
            content=response_content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
        )
    )
    return client


def _sample_input(num_docs: int = 1, chunks_per_doc: int = 1) -> list[dict]:
    """Build Refiner-style input data with the given number of docs/chunks."""
    docs = []
    for d in range(num_docs):
        chunks = []
        for c in range(chunks_per_doc):
            chunks.append(
                {
                    "content": f"Chunk {c} of document {d} about renewable energy.",
                    "token_count": 150,
                    "chunk_index": c,
                    "metadata": {
                        "source_url": f"https://example.com/doc-{d}",
                        "language": "en",
                        "title": f"Document {d}",
                    },
                }
            )
        docs.append(
            {
                "url": f"https://example.com/doc-{d}",
                "title": f"Document {d}",
                "language": "en",
                "content": f"Full text of document {d}...",
                "chunks": chunks,
            }
        )
    return docs


# ---------------------------------------------------------------------------
# Stage identity
# ---------------------------------------------------------------------------

class TestFactoryStageBasics:
    def test_factory_stage_name(self) -> None:
        stage = FactoryStage(llm_client=_mock_llm_client())
        assert stage.stage_name == "factory"


# ---------------------------------------------------------------------------
# validate_input
# ---------------------------------------------------------------------------

class TestValidateInput:
    async def test_validate_input_valid(self) -> None:
        stage = FactoryStage(llm_client=_mock_llm_client())
        data = _sample_input()
        assert await stage.validate_input(data) is True

    async def test_validate_input_valid_multiple_docs(self) -> None:
        stage = FactoryStage(llm_client=_mock_llm_client())
        data = _sample_input(num_docs=3, chunks_per_doc=2)
        assert await stage.validate_input(data) is True

    async def test_validate_input_invalid_empty_list(self) -> None:
        stage = FactoryStage(llm_client=_mock_llm_client())
        assert await stage.validate_input([]) is False

    async def test_validate_input_invalid_not_list(self) -> None:
        stage = FactoryStage(llm_client=_mock_llm_client())
        assert await stage.validate_input("not a list") is False

    async def test_validate_input_invalid_missing_chunks(self) -> None:
        stage = FactoryStage(llm_client=_mock_llm_client())
        data = [{"url": "https://example.com", "title": "T", "content": "text"}]
        assert await stage.validate_input(data) is False

    async def test_validate_input_invalid_chunks_not_list(self) -> None:
        stage = FactoryStage(llm_client=_mock_llm_client())
        data = [{"url": "https://example.com", "chunks": "not a list"}]
        assert await stage.validate_input(data) is False

    async def test_validate_input_invalid_non_dict_item(self) -> None:
        stage = FactoryStage(llm_client=_mock_llm_client())
        assert await stage.validate_input(["not a dict"]) is False


# ---------------------------------------------------------------------------
# process -- single chunk
# ---------------------------------------------------------------------------

class TestProcessGeneratesExamples:
    async def test_process_generates_examples(self) -> None:
        """Single chunk should produce examples from LLM response."""
        llm = _mock_llm_client(
            response_content='[{"input":"What is energy?","output":"Energy is..."}]'
        )
        stage = FactoryStage(llm_client=llm)
        data = _sample_input(num_docs=1, chunks_per_doc=1)

        result = await stage.process(data, config={})

        assert isinstance(result, StageResult)
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["input"] == "What is energy?"
        assert result.data[0]["output"] == "Energy is..."

    async def test_process_returns_stage_result(self) -> None:
        stage = FactoryStage(llm_client=_mock_llm_client())
        data = _sample_input()
        result = await stage.process(data, config={})
        assert isinstance(result, StageResult)


# ---------------------------------------------------------------------------
# process -- multiple chunks
# ---------------------------------------------------------------------------

class TestProcessMultipleChunks:
    async def test_process_multiple_chunks(self) -> None:
        """Multiple chunks across multiple documents should all be processed."""
        llm = _mock_llm_client(
            response_content='[{"input":"Q1","output":"A1"},{"input":"Q2","output":"A2"}]'
        )
        stage = FactoryStage(llm_client=llm)
        # 2 docs, each with 2 chunks => 4 LLM calls => 4 * 2 = 8 examples
        data = _sample_input(num_docs=2, chunks_per_doc=2)

        result = await stage.process(data, config={})

        assert result.success is True
        assert len(result.data) == 8  # 4 chunks * 2 examples each
        assert llm.complete.call_count == 4

    async def test_process_single_doc_multiple_chunks(self) -> None:
        llm = _mock_llm_client()
        stage = FactoryStage(llm_client=llm)
        data = _sample_input(num_docs=1, chunks_per_doc=5)

        result = await stage.process(data, config={})

        assert result.success is True
        assert llm.complete.call_count == 5
        assert len(result.data) == 5  # 5 chunks * 1 example each


# ---------------------------------------------------------------------------
# process -- template configuration
# ---------------------------------------------------------------------------

class TestProcessUsesConfiguredTemplate:
    async def test_process_uses_configured_template(self) -> None:
        """The template name from config should be looked up in TemplateRegistry."""
        llm = _mock_llm_client()
        stage = FactoryStage(llm_client=llm)
        data = _sample_input()

        with patch("pipeline.stages.generation.TemplateRegistry") as mock_reg:
            mock_template = MagicMock()
            mock_template.template_type = "summarization"
            mock_template.system_prompt = "System prompt"
            mock_template.render.return_value = "rendered prompt"
            mock_template.parse_response.return_value = [
                {"input": "Q", "output": "A"}
            ]
            mock_reg.get.return_value = mock_template

            result = await stage.process(
                data, config={"template": "summarization"}
            )

        mock_reg.get.assert_called_once_with("summarization")
        assert result.success is True

    async def test_process_defaults_to_qa_template(self) -> None:
        """Without template config, the default 'qa' template should be used."""
        llm = _mock_llm_client()
        stage = FactoryStage(llm_client=llm)
        data = _sample_input()

        with patch("pipeline.stages.generation.TemplateRegistry") as mock_reg:
            mock_template = MagicMock()
            mock_template.template_type = "qa"
            mock_template.system_prompt = "System prompt"
            mock_template.render.return_value = "rendered prompt"
            mock_template.parse_response.return_value = [
                {"input": "Q", "output": "A"}
            ]
            mock_reg.get.return_value = mock_template

            await stage.process(data, config={})

        mock_reg.get.assert_called_once_with("qa")


# ---------------------------------------------------------------------------
# process -- token and cost tracking
# ---------------------------------------------------------------------------

class TestProcessTracksTokensAndCost:
    async def test_process_tracks_tokens_and_cost(self) -> None:
        """Stats should aggregate token counts and cost across all chunks."""
        llm = _mock_llm_client(total_tokens=200, cost=0.002)
        stage = FactoryStage(llm_client=llm)
        data = _sample_input(num_docs=1, chunks_per_doc=3)

        result = await stage.process(data, config={})

        assert result.stats["total_tokens"] == 600  # 3 chunks * 200 tokens
        assert result.stats["total_cost"] == pytest.approx(0.006)  # 3 * 0.002

    async def test_stats_include_required_keys(self) -> None:
        llm = _mock_llm_client()
        stage = FactoryStage(llm_client=llm)
        data = _sample_input()

        result = await stage.process(data, config={})

        assert "total_examples" in result.stats
        assert "total_tokens" in result.stats
        assert "total_cost" in result.stats
        assert "template" in result.stats
        assert "model" in result.stats

    async def test_stats_total_examples_matches_data(self) -> None:
        llm = _mock_llm_client(
            response_content='[{"input":"Q1","output":"A1"},{"input":"Q2","output":"A2"}]'
        )
        stage = FactoryStage(llm_client=llm)
        data = _sample_input(num_docs=1, chunks_per_doc=2)

        result = await stage.process(data, config={})

        assert result.stats["total_examples"] == len(result.data)
        assert result.stats["total_examples"] == 4  # 2 chunks * 2 examples


# ---------------------------------------------------------------------------
# process -- LLM error handling
# ---------------------------------------------------------------------------

class TestProcessHandlesLLMError:
    async def test_process_handles_llm_error(self) -> None:
        """LLM exceptions should be captured in errors, not crash the stage."""
        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=RuntimeError("API timeout"))
        stage = FactoryStage(llm_client=llm)
        data = _sample_input()

        result = await stage.process(data, config={})

        assert result.success is True  # partial success
        assert len(result.data) == 0
        assert len(result.errors) >= 1
        assert "API timeout" in result.errors[0]

    async def test_process_partial_failure(self) -> None:
        """If one chunk fails and another succeeds, we get partial results."""
        responses = [
            LLMResponse(
                content='[{"input":"Q","output":"A"}]',
                model="gpt-4o-mini",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                cost=0.001,
            ),
            RuntimeError("Chunk 2 failed"),
        ]
        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=responses)
        stage = FactoryStage(llm_client=llm)
        data = _sample_input(num_docs=1, chunks_per_doc=2)

        result = await stage.process(data, config={})

        assert result.success is True
        assert len(result.data) == 1
        assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# process -- parse failure
# ---------------------------------------------------------------------------

class TestProcessHandlesParseFailure:
    async def test_process_handles_parse_failure(self) -> None:
        """If LLM returns non-JSON, parse_response returns [] -- no examples."""
        llm = _mock_llm_client(response_content="This is not JSON at all")
        stage = FactoryStage(llm_client=llm)
        data = _sample_input()

        result = await stage.process(data, config={})

        assert result.success is True
        # parse_response on base PromptTemplate returns [] for invalid JSON
        assert len(result.data) == 0
        # tokens/cost should still be tracked even if parsing yields nothing
        assert result.stats["total_tokens"] == 150
        assert result.stats["total_cost"] == pytest.approx(0.001)


# ---------------------------------------------------------------------------
# Example fields
# ---------------------------------------------------------------------------

class TestExamplesHaveRequiredFields:
    async def test_examples_have_required_fields(self) -> None:
        """Each enriched example must have all expected metadata fields."""
        llm = _mock_llm_client(
            response_content='[{"input":"Question?","output":"Answer."}]'
        )
        stage = FactoryStage(llm_client=llm)
        data = _sample_input()

        result = await stage.process(data, config={})

        assert len(result.data) == 1
        example = result.data[0]

        required_fields = {
            "input",
            "output",
            "template_type",
            "model_used",
            "token_count",
            "cost",
            "source_chunk",
            "source_url",
        }
        assert required_fields.issubset(example.keys()), (
            f"Missing fields: {required_fields - example.keys()}"
        )

    async def test_example_values_are_correct(self) -> None:
        """Verify enriched field values match expected data."""
        llm = _mock_llm_client(
            response_content='[{"input":"Q","output":"A"}]',
            model="gpt-4o-mini",
            total_tokens=150,
            cost=0.001,
        )
        stage = FactoryStage(llm_client=llm)
        data = _sample_input()

        result = await stage.process(data, config={})

        ex = result.data[0]
        assert ex["input"] == "Q"
        assert ex["output"] == "A"
        assert ex["model_used"] == "gpt-4o-mini"
        assert ex["token_count"] == 150
        assert ex["cost"] == pytest.approx(0.001)  # 1 example, full cost
        assert ex["source_url"] == "https://example.com/doc-0"

    async def test_cost_distributed_across_examples(self) -> None:
        """When multiple examples come from one chunk, cost is split evenly."""
        llm = _mock_llm_client(
            response_content='[{"input":"Q1","output":"A1"},{"input":"Q2","output":"A2"}]',
            cost=0.01,
        )
        stage = FactoryStage(llm_client=llm)
        data = _sample_input()

        result = await stage.process(data, config={})

        assert len(result.data) == 2
        assert result.data[0]["cost"] == pytest.approx(0.005)
        assert result.data[1]["cost"] == pytest.approx(0.005)

    async def test_source_chunk_is_truncated(self) -> None:
        """The source_chunk field should be truncated to 200 chars."""
        long_text = "A" * 500
        data = [
            {
                "url": "https://example.com/doc",
                "title": "Doc",
                "language": "en",
                "content": long_text,
                "chunks": [
                    {
                        "content": long_text,
                        "token_count": 200,
                        "chunk_index": 0,
                        "metadata": {
                            "source_url": "https://example.com/doc",
                            "language": "en",
                            "title": "Doc",
                        },
                    }
                ],
            }
        ]
        llm = _mock_llm_client()
        stage = FactoryStage(llm_client=llm)

        result = await stage.process(data, config={})

        assert len(result.data[0]["source_chunk"]) <= 200


# ---------------------------------------------------------------------------
# Config passthrough
# ---------------------------------------------------------------------------

class TestConfigPassthrough:
    async def test_model_config_passed_to_llm(self) -> None:
        """The model from config should be forwarded to LLMClient.complete."""
        llm = _mock_llm_client()
        stage = FactoryStage(llm_client=llm)
        data = _sample_input()

        await stage.process(data, config={"model": "gpt-4o"})

        call_kwargs = llm.complete.call_args
        assert call_kwargs.kwargs.get("model") == "gpt-4o" or call_kwargs[1].get("model") == "gpt-4o"

    async def test_temperature_config_passed_to_llm(self) -> None:
        """The temperature from config should be forwarded to LLMClient.complete."""
        llm = _mock_llm_client()
        stage = FactoryStage(llm_client=llm)
        data = _sample_input()

        await stage.process(data, config={"temperature": 0.3})

        call_kwargs = llm.complete.call_args
        assert (
            call_kwargs.kwargs.get("temperature") == 0.3
            or call_kwargs[1].get("temperature") == 0.3
        )
