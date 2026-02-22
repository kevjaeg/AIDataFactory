"""Jinja2-based prompt template system for training data generation.

Usage::

    from templates import TemplateRegistry

    tmpl = TemplateRegistry.get("qa")
    user_prompt = tmpl.render(content="...", metadata={"num_examples": 5})
    system_msg  = tmpl.system_prompt
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from templates.base import PromptTemplate
from templates.classification import ClassificationTemplate
from templates.instruction_following import InstructionTemplate
from templates.qa_generation import QATemplate
from templates.summarization import SummarizationTemplate


class DynamicTemplate(PromptTemplate):
    """A template constructed from DB-stored data (custom templates)."""

    def __init__(
        self,
        name: str,
        template_type: str,
        system_prompt_text: str,
        user_prompt_template_text: str,
        output_schema_data: dict[str, Any] | None = None,
    ) -> None:
        self.template_type = template_type
        self._name = name
        self._system_prompt = system_prompt_text
        self._user_prompt_template = user_prompt_template_text
        self._output_schema = output_schema_data or {}

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def user_prompt_template(self) -> str:
        return self._user_prompt_template

    @property
    def output_schema(self) -> dict[str, Any]:
        return self._output_schema


# Built-in template classes (immutable)
_BUILTIN_TEMPLATES: dict[str, type[PromptTemplate]] = {
    "qa": QATemplate,
    "summarization": SummarizationTemplate,
    "classification": ClassificationTemplate,
    "instruction": InstructionTemplate,
}


class TemplateRegistry:
    """Registry that maps short names to prompt-template classes or instances."""

    _templates: dict[str, type[PromptTemplate]] = dict(_BUILTIN_TEMPLATES)
    _custom_instances: dict[str, DynamicTemplate] = {}

    @classmethod
    def get(cls, name: str) -> PromptTemplate:
        """Return a fresh template instance for *name*.

        Raises :class:`ValueError` if the name is not registered.
        """
        # Check custom instances first
        if name in cls._custom_instances:
            return cls._custom_instances[name]
        if name not in cls._templates:
            available = cls.list_templates()
            raise ValueError(f"Unknown template: {name}. Available: {available}")
        return cls._templates[name]()

    @classmethod
    def list_templates(cls) -> list[str]:
        """Return the names of all registered templates (built-in + custom)."""
        names = list(cls._templates.keys())
        for name in cls._custom_instances:
            if name not in names:
                names.append(name)
        return names

    @classmethod
    def is_builtin(cls, name: str) -> bool:
        """Check if a template name is a built-in template."""
        return name in _BUILTIN_TEMPLATES

    @classmethod
    def register_custom(cls, template_row) -> None:
        """Register a custom template from a DB model row."""
        cls._custom_instances[template_row.name] = DynamicTemplate(
            name=template_row.name,
            template_type=template_row.template_type,
            system_prompt_text=template_row.system_prompt,
            user_prompt_template_text=template_row.user_prompt_template,
            output_schema_data=template_row.output_schema,
        )
        logger.debug(f"Registered custom template: {template_row.name}")

    @classmethod
    def unregister_custom(cls, name: str) -> None:
        """Remove a custom template from the registry."""
        cls._custom_instances.pop(name, None)
        logger.debug(f"Unregistered custom template: {name}")

    @classmethod
    async def load_custom_templates(cls, session: AsyncSession) -> None:
        """Load all custom templates from the database into the registry."""
        from db.models import CustomTemplate

        result = await session.execute(select(CustomTemplate))
        templates = result.scalars().all()
        for tmpl in templates:
            cls.register_custom(tmpl)
        logger.info(f"Loaded {len(templates)} custom template(s) from database")


__all__ = [
    "PromptTemplate",
    "DynamicTemplate",
    "TemplateRegistry",
    "QATemplate",
    "SummarizationTemplate",
    "ClassificationTemplate",
    "InstructionTemplate",
]
