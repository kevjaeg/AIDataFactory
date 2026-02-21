"""Q&A prompt template -- generates question-answer pairs from content."""

from __future__ import annotations

from typing import Any

from templates.base import PromptTemplate


class QATemplate(PromptTemplate):
    """Generate question-answer pairs that test understanding of key concepts."""

    template_type: str = "qa"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a high-quality training-data generator. Given a text passage, "
            "produce question-answer pairs that test comprehension of the key facts, "
            "concepts, and relationships in the text. Each question should be "
            "self-contained and answerable solely from the passage.\n\n"
            "Return your output as a JSON array of objects. Each object must have "
            'exactly two keys: "input" (the question) and "output" (the answer). '
            "Do not include any text outside the JSON array."
        )

    @property
    def user_prompt_template(self) -> str:
        return (
            "Generate {{ num_examples | default(3) }} question-answer pairs from the "
            "following text:\n\n"
            "---\n"
            "{{ content }}\n"
            "---\n\n"
            "{% if metadata.title %}Source: {{ metadata.title }}\n\n{% endif %}"
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
                        "description": "A question about the content.",
                    },
                    "output": {
                        "type": "string",
                        "description": "The correct answer derived from the content.",
                    },
                },
                "required": ["input", "output"],
            },
        }
