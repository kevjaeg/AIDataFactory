"""Jinja2-based prompt template system for training data generation.

Usage::

    from templates import TemplateRegistry

    tmpl = TemplateRegistry.get("qa")
    user_prompt = tmpl.render(content="...", metadata={"num_examples": 5})
    system_msg  = tmpl.system_prompt
"""

from __future__ import annotations

from templates.base import PromptTemplate
from templates.classification import ClassificationTemplate
from templates.instruction_following import InstructionTemplate
from templates.qa_generation import QATemplate
from templates.summarization import SummarizationTemplate


class TemplateRegistry:
    """Registry that maps short names to prompt-template classes."""

    _templates: dict[str, type[PromptTemplate]] = {
        "qa": QATemplate,
        "summarization": SummarizationTemplate,
        "classification": ClassificationTemplate,
        "instruction": InstructionTemplate,
    }

    @classmethod
    def get(cls, name: str) -> PromptTemplate:
        """Return a fresh template instance for *name*.

        Raises :class:`ValueError` if the name is not registered.
        """
        if name not in cls._templates:
            available = list(cls._templates.keys())
            raise ValueError(f"Unknown template: {name}. Available: {available}")
        return cls._templates[name]()

    @classmethod
    def list_templates(cls) -> list[str]:
        """Return the names of all registered templates."""
        return list(cls._templates.keys())


__all__ = [
    "PromptTemplate",
    "TemplateRegistry",
    "QATemplate",
    "SummarizationTemplate",
    "ClassificationTemplate",
    "InstructionTemplate",
]
