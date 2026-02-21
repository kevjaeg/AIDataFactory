"""Classification prompt template -- generates (text, label) pairs."""

from __future__ import annotations

from typing import Any

from templates.base import PromptTemplate


class ClassificationTemplate(PromptTemplate):
    """Generate text-classification training pairs with configurable labels."""

    template_type: str = "classification"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a high-quality training-data generator specializing in text "
            "classification. Given a text passage and a set of category labels, "
            "produce training examples where each example contains a short text "
            'snippet ("input") and the most appropriate category label ("output"). '
            "The generated texts should be realistic and clearly belong to the "
            "assigned category.\n\n"
            "Return your output as a JSON array of objects. Each object must have "
            'exactly two keys: "input" (the text to classify) and "output" (the '
            "category label). "
            "Do not include any text outside the JSON array."
        )

    @property
    def user_prompt_template(self) -> str:
        return (
            "Generate {{ num_examples | default(3) }} classification training examples "
            "inspired by the following text:\n\n"
            "---\n"
            "{{ content }}\n"
            "---\n\n"
            "{% if metadata.labels %}"
            "Use ONLY the following labels: {{ metadata.labels | join(', ') }}\n\n"
            "{% endif %}"
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
                        "description": "A text snippet to be classified.",
                    },
                    "output": {
                        "type": "string",
                        "description": "The category label for the text.",
                    },
                },
                "required": ["input", "output"],
            },
        }
