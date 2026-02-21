import asyncio

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from clients.llm_client import LLMClient, LLMResponse


def _make_mock_response(
    content: str = "Test response",
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    total_tokens: int = 30,
) -> MagicMock:
    """Helper to build a mock litellm response object."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=content))]
    mock_response.usage = MagicMock(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    return mock_response


@patch("clients.llm_client.litellm")
async def test_complete_returns_llm_response(mock_litellm: MagicMock) -> None:
    """complete() should return an LLMResponse dataclass."""
    mock_response = _make_mock_response()
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)
    mock_litellm.completion_cost.return_value = 0.001

    client = LLMClient()
    result = await client.complete("Hello", model="gpt-4o-mini")

    assert isinstance(result, LLMResponse)
    assert result.content == "Test response"
    assert result.model == "gpt-4o-mini"


@patch("clients.llm_client.litellm")
async def test_complete_with_system_prompt(mock_litellm: MagicMock) -> None:
    """When system_prompt is provided, it should appear as the first message."""
    mock_response = _make_mock_response()
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)
    mock_litellm.completion_cost.return_value = 0.001

    client = LLMClient()
    await client.complete("Hello", model="gpt-4o-mini", system_prompt="You are helpful")

    call_kwargs = mock_litellm.acompletion.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0] == {"role": "system", "content": "You are helpful"}
    assert messages[1] == {"role": "user", "content": "Hello"}


@patch("clients.llm_client.litellm")
async def test_complete_without_system_prompt(mock_litellm: MagicMock) -> None:
    """Without system_prompt, messages should contain only the user message."""
    mock_response = _make_mock_response()
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)
    mock_litellm.completion_cost.return_value = 0.001

    client = LLMClient()
    await client.complete("Hello", model="gpt-4o-mini")

    call_kwargs = mock_litellm.acompletion.call_args.kwargs
    messages = call_kwargs["messages"]
    assert len(messages) == 1
    assert messages[0] == {"role": "user", "content": "Hello"}


@patch("clients.llm_client.litellm")
async def test_complete_includes_token_counts(mock_litellm: MagicMock) -> None:
    """Token counts from the response should be forwarded into LLMResponse."""
    mock_response = _make_mock_response(
        prompt_tokens=15,
        completion_tokens=25,
        total_tokens=40,
    )
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)
    mock_litellm.completion_cost.return_value = 0.002

    client = LLMClient()
    result = await client.complete("Hello", model="gpt-4o-mini")

    assert result.prompt_tokens == 15
    assert result.completion_tokens == 25
    assert result.total_tokens == 40


@patch("clients.llm_client.litellm")
async def test_complete_includes_cost(mock_litellm: MagicMock) -> None:
    """Cost should be calculated via litellm.completion_cost()."""
    mock_response = _make_mock_response()
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)
    mock_litellm.completion_cost.return_value = 0.00345

    client = LLMClient()
    result = await client.complete("Hello", model="gpt-4o-mini")

    mock_litellm.completion_cost.assert_called_once_with(completion_response=mock_response)
    assert result.cost == 0.00345


@patch("clients.llm_client.litellm")
async def test_retry_on_rate_limit(mock_litellm: MagicMock) -> None:
    """A 429 rate-limit error should be retried, then succeed."""
    rate_limit_error = Exception("Rate limit exceeded")
    rate_limit_error.status_code = 429

    mock_litellm.RateLimitError = type("RateLimitError", (Exception,), {})

    mock_response = _make_mock_response(content="Retry success")
    mock_litellm.acompletion = AsyncMock(
        side_effect=[rate_limit_error, mock_response],
    )
    mock_litellm.completion_cost.return_value = 0.001

    client = LLMClient(max_retries=3)

    with patch("clients.llm_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await client.complete("Hello", model="gpt-4o-mini")

    assert result.content == "Retry success"
    assert mock_litellm.acompletion.call_count == 2
    mock_sleep.assert_called_once_with(1)  # first backoff = 1s


@patch("clients.llm_client.litellm")
async def test_retry_exhausted_raises(mock_litellm: MagicMock) -> None:
    """After max_retries, the rate-limit error should be re-raised."""
    rate_limit_error = Exception("Rate limit exceeded")
    rate_limit_error.status_code = 429

    mock_litellm.RateLimitError = type("RateLimitError", (Exception,), {})

    mock_litellm.acompletion = AsyncMock(
        side_effect=[rate_limit_error, rate_limit_error, rate_limit_error],
    )

    client = LLMClient(max_retries=3)

    with patch("clients.llm_client.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await client.complete("Hello", model="gpt-4o-mini")

    assert mock_litellm.acompletion.call_count == 3


@patch("clients.llm_client.litellm")
async def test_concurrency_limited(mock_litellm: MagicMock) -> None:
    """The semaphore should limit concurrent LLM calls."""
    call_count = 0
    max_concurrent_seen = 0
    current_concurrent = 0

    async def mock_acompletion(**kwargs):
        nonlocal call_count, max_concurrent_seen, current_concurrent
        current_concurrent += 1
        max_concurrent_seen = max(max_concurrent_seen, current_concurrent)
        await asyncio.sleep(0.05)
        current_concurrent -= 1
        call_count += 1
        return _make_mock_response()

    mock_litellm.acompletion = mock_acompletion
    mock_litellm.completion_cost.return_value = 0.001
    mock_litellm.RateLimitError = type("RateLimitError", (Exception,), {})

    max_concurrent = 2
    client = LLMClient(max_concurrent=max_concurrent)

    # Launch more tasks than the concurrency limit
    tasks = [client.complete(f"Prompt {i}", model="gpt-4o-mini") for i in range(6)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 6
    assert all(isinstance(r, LLMResponse) for r in results)
    assert max_concurrent_seen <= max_concurrent


@patch("clients.llm_client.litellm")
async def test_default_model(mock_litellm: MagicMock) -> None:
    """When no model is specified, gpt-4o-mini should be used by default."""
    mock_response = _make_mock_response()
    mock_litellm.acompletion = AsyncMock(return_value=mock_response)
    mock_litellm.completion_cost.return_value = 0.001

    client = LLMClient()
    result = await client.complete("Hello")

    call_kwargs = mock_litellm.acompletion.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert result.model == "gpt-4o-mini"
