import asyncio
from dataclasses import dataclass

import litellm
from loguru import logger


@dataclass
class LLMResponse:
    """Response from an LLM completion call."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float


class LLMClient:
    """Async LLM client wrapping litellm with cost tracking and concurrency control."""

    def __init__(self, max_concurrent: int = 5, max_retries: int = 3) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_retries = max_retries

    async def complete(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Send a completion request to the LLM via litellm.

        Args:
            prompt: The user prompt to send.
            model: The model identifier (e.g. "gpt-4o-mini").
            temperature: Sampling temperature (0.0 - 2.0).
            system_prompt: Optional system prompt prepended to messages.

        Returns:
            LLMResponse with content, token counts, and cost.

        Raises:
            Exception: After max retries exhausted on rate-limit errors.
        """
        messages: list[dict[str, str]] = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with self._semaphore:
            return await self._call_with_retries(
                model=model,
                messages=messages,
                temperature=temperature,
            )

    async def _call_with_retries(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> LLMResponse:
        """Call litellm.acompletion with exponential-backoff retry on rate limits."""
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )

                cost = litellm.completion_cost(completion_response=response)

                return LLMResponse(
                    content=response.choices[0].message.content,
                    model=model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    cost=cost,
                )

            except Exception as e:
                if self._is_rate_limit_error(e):
                    last_error = e
                    backoff = 2**attempt  # 1s, 2s, 4s
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}/{self._max_retries}), "
                        f"retrying in {backoff}s"
                    )
                    await asyncio.sleep(backoff)
                else:
                    raise

        # All retries exhausted
        raise last_error  # type: ignore[misc]

    @staticmethod
    def _is_rate_limit_error(error: Exception) -> bool:
        """Check whether an exception represents a 429 rate-limit error."""
        if isinstance(error, litellm.RateLimitError):
            return True
        if hasattr(error, "status_code") and error.status_code == 429:
            return True
        return False
