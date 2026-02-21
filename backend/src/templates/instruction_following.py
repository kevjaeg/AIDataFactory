"""Instruction-following prompt template -- generates (instruction, response) pairs."""

from __future__ import annotations

from typing import Any

from templates.base import PromptTemplate


class InstructionTemplate(PromptTemplate):
    """Generate instruction-response pairs grounded in the provided content."""

    template_type: str = "instruction"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a high-quality training-data generator specializing in "
            "instruction-following examples. Given a text passage, produce training "
            "pairs where each pair consists of a clear, actionable instruction "
            '("input") and a detailed, helpful response ("output") that draws on '
            "information from the passage. The instructions should feel natural -- "
            "the kind a real user might ask -- and the responses should be thorough "
            "yet concise.\n\n"
            "Return your output as a JSON array of objects. Each object must have "
            'exactly two keys: "input" (the instruction) and "output" (the response). '
            "Do not include any text outside the JSON array."
        )

    @property
    def user_prompt_template(self) -> str:
        return (
            "Generate {{ num_examples | default(3) }} instruction-response training "
            "examples from the following text:\n\n"
            "---\n"
            "{{ content }}\n"
            "---\n\n"
            "{% if metadata.title %}Source: {{ metadata.title }}\n\n{% endif %}"
            "{% if metadata.difficulty %}"
            "Target difficulty level: {{ metadata.difficulty }}\n\n"
            "{% endif %}"
            "Return your response as a JSON array."
        )

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "An instruction or task for the model to follow.",
                    },
                    "output": {
                        "type": "string",
                        "description": "A detailed response to the instruction.",
                    },
                },
                "required": ["input", "output"],
            },
        }
