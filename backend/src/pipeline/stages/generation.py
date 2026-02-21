"""Factory stage: generate training examples from processed text chunks via LLM."""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from clients.llm_client import LLMClient
from pipeline.base import PipelineStage, StageResult
from templates import TemplateRegistry


class FactoryStage(PipelineStage):
    """Stage 3 (Factory): generate training examples from chunks using LLM calls.

    For each chunk produced by the Refiner stage, this stage:

    1. Renders a prompt using the configured :class:`PromptTemplate`.
    2. Calls the LLM via :class:`LLMClient` (respecting its concurrency semaphore).
    3. Parses the LLM response into structured training examples.
    4. Enriches each example with metadata (template type, model, cost, source).

    Configuration keys (passed via *config* dict):

    * ``template`` -- template name registered in :class:`TemplateRegistry` (default ``"qa"``).
    * ``model`` -- LLM model identifier (default ``"gpt-4o-mini"``).
    * ``examples_per_chunk`` -- hint passed to the template (default ``3``).
    * ``temperature`` -- sampling temperature (default ``0.7``).
    """

    stage_name = "factory"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or LLMClient()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_input(self, input_data: Any) -> bool:
        """Input must be a non-empty list of Refiner output dicts with ``chunks``."""
        if not isinstance(input_data, list) or len(input_data) == 0:
            return False
        for doc in input_data:
            if not isinstance(doc, dict):
                return False
            if "chunks" not in doc or not isinstance(doc["chunks"], list):
                return False
        return True

    # ------------------------------------------------------------------
    # Main processing
    # ------------------------------------------------------------------

    async def process(self, input_data: list[dict], config: dict) -> StageResult:
        """Generate training examples for every chunk in *input_data*."""
        template_name = config.get("template", "qa")
        model = config.get("model", "gpt-4o-mini")
        examples_per_chunk = config.get("examples_per_chunk", 3)
        temperature = config.get("temperature", 0.7)

        template = TemplateRegistry.get(template_name)

        results: list[dict[str, Any]] = []
        errors: list[str] = []
        total_tokens = 0
        total_cost = 0.0

        # Build one task per chunk across all documents
        tasks: list[asyncio.Task] = []
        for doc in input_data:
            for chunk in doc["chunks"]:
                tasks.append(
                    self._generate_examples(
                        chunk, template, model, examples_per_chunk, temperature
                    )
                )

        # Process concurrently (bounded by LLMClient's internal semaphore)
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for response in responses:
            if isinstance(response, Exception):
                errors.append(str(response))
                logger.warning(f"Factory chunk error: {response}")
                continue
            examples, tokens, cost = response
            results.extend(examples)
            total_tokens += tokens
            total_cost += cost

        return StageResult(
            success=True,
            data=results,
            errors=errors,
            stats={
                "total_examples": len(results),
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "template": template_name,
                "model": model,
            },
        )

    # ------------------------------------------------------------------
    # Per-chunk generation
    # ------------------------------------------------------------------

    async def _generate_examples(
        self,
        chunk: dict[str, Any],
        template,
        model: str,
        examples_per_chunk: int,
        temperature: float,
    ) -> tuple[list[dict[str, Any]], int, float]:
        """Generate training examples for a single chunk.

        Returns ``(enriched_examples, total_tokens, cost)``.
        """
        metadata = dict(chunk.get("metadata", {}))
        metadata["num_examples"] = examples_per_chunk

        prompt = template.render(content=chunk["content"], metadata=metadata)
        response = await self._llm.complete(
            prompt=prompt,
            model=model,
            temperature=temperature,
            system_prompt=template.system_prompt,
        )

        examples = template.parse_response(response.content)

        # Enrich each example with provenance metadata
        enriched: list[dict[str, Any]] = []
        num_examples = max(len(examples), 1)
        for ex in examples:
            enriched.append(
                {
                    "input": ex["input"],
                    "output": ex["output"],
                    "template_type": template.template_type,
                    "model_used": response.model,
                    "token_count": response.total_tokens,
                    "cost": response.cost / num_examples,
                    "source_chunk": chunk["content"][:200],
                    "source_url": metadata.get("source_url", ""),
                }
            )

        return enriched, response.total_tokens, response.cost
