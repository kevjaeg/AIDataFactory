"""Summarization prompt template -- generates (long_text, summary) pairs."""

from __future__ import annotations

from typing import Any

from templates.base import PromptTemplate


class SummarizationTemplate(PromptTemplate):
    """Generate training pairs of long passages and their concise summaries."""

    template_type: str = "summarization"

    @property
    def system_prompt(self) -> str:
        return (
            "You are a high-quality training-data generator specializing in "
            "summarization. Given a text passage, produce training examples where "
            'each example contains a passage ("input") and a concise, accurate '
            'summary of that passage ("output"). The summaries should capture the '
            "main ideas while being significantly shorter than the original text.\n\n"
            "Return your output as a JSON array of objects. Each object must have "
            'exactly two keys: "input" (the passage or a section of the passage) '
            'and "output" (the summary). '
            "Do not include any text outside the JSON array."
        )

    @property
    def user_prompt_template(self) -> str:
        return (
            "Generate {{ num_examples | default(3) }} summarization training examples "
            "from the following text. For each example, select a meaningful section of "
            "the text as the input and write a concise summary as the output.\n\n"
            "---\n"
            "{{ content }}\n"
            "---\n\n"
            "{% if metadata.title %}Source: {{ metadata.title }}\n\n{% endif %}"
            "{% if metadata.summary_style %}Desired summary style: {{ metadata.summary_style }}\n\n{% endif %}"
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
                        "description": "A passage of text to be summarized.",
                    },
                    "output": {
                        "type": "string",
                        "description": "A concise summary of the passage.",
                    },
                },
                "required": ["input", "output"],
            },
        }
