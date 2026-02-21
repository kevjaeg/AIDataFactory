"""Base class for Jinja2-based prompt templates."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from jinja2 import Template


class PromptTemplate(ABC):
    """Base class for all prompt templates.

    Each concrete template defines a *system_prompt* (sent as the system
    message), a *user_prompt_template* (a Jinja2 string rendered with the
    chunk content and optional metadata), and an *output_schema* that
    describes the expected JSON structure returned by the LLM.
    """

    template_type: str  # "qa", "summarization", "classification", "instruction"

    # ------------------------------------------------------------------
    # Abstract properties that every template must implement
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt sent to the LLM."""
        ...

    @property
    @abstractmethod
    def user_prompt_template(self) -> str:
        """Jinja2 template string for the user prompt."""
        ...

    @property
    @abstractmethod
    def output_schema(self) -> dict[str, Any]:
        """JSON-schema-like description of the expected output."""
        ...

    # ------------------------------------------------------------------
    # Concrete helpers shared by all templates
    # ------------------------------------------------------------------

    def render(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Render the user prompt with *content* and optional *metadata*.

        The Jinja2 template receives two top-level variables:

        * ``content`` -- the raw text chunk to process.
        * ``metadata`` -- an arbitrary dict of extra context (title, labels,
          num_examples, etc.).  Individual keys are also accessible directly
          inside the template for convenience (e.g. ``{{ num_examples }}``).
        """
        ctx: dict[str, Any] = {"content": content, "metadata": metadata or {}}
        # Flatten metadata keys into the top-level context so templates can
        # use e.g. {{ num_examples }} instead of {{ metadata.num_examples }}.
        ctx.update(metadata or {})
        template = Template(self.user_prompt_template)
        return template.render(**ctx)

    def parse_response(self, response: str) -> list[dict[str, str]]:
        """Parse an LLM response into structured training examples.

        The LLM is expected to return JSON -- either a JSON **array** of
        objects or a single JSON **object**.  Each object should contain
        ``input`` and ``output`` keys.

        Returns a list of dicts: ``[{"input": "...", "output": "..."}, ...]``.
        An empty list is returned when the response cannot be parsed.
        """
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return [
                    {"input": str(item.get("input", "")), "output": str(item.get("output", ""))}
                    for item in data
                    if isinstance(item, dict)
                ]
            elif isinstance(data, dict):
                return [{"input": str(data.get("input", "")), "output": str(data.get("output", ""))}]
        except json.JSONDecodeError:
            return []
        return []
