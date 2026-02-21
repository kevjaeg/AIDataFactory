"""Tests for the Jinja2-based prompt template system."""

import json

import pytest

from templates import TemplateRegistry
from templates.base import PromptTemplate
from templates.qa_generation import QATemplate
from templates.summarization import SummarizationTemplate
from templates.classification import ClassificationTemplate
from templates.instruction_following import InstructionTemplate


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestTemplateRegistry:
    def test_registry_lists_all_templates(self):
        names = TemplateRegistry.list_templates()
        assert sorted(names) == ["classification", "instruction", "qa", "summarization"]

    def test_registry_get_returns_template_instance(self):
        for name in ("qa", "summarization", "classification", "instruction"):
            tmpl = TemplateRegistry.get(name)
            assert isinstance(tmpl, PromptTemplate)

    def test_registry_get_unknown_raises_error(self):
        with pytest.raises(ValueError, match="Unknown template"):
            TemplateRegistry.get("nonexistent")


# ---------------------------------------------------------------------------
# Q&A template tests
# ---------------------------------------------------------------------------

class TestQATemplate:
    def test_qa_template_renders_with_content(self):
        tmpl = QATemplate()
        rendered = tmpl.render(content="The sky is blue because of Rayleigh scattering.")
        assert "The sky is blue because of Rayleigh scattering." in rendered
        # Default num_examples should appear
        assert "3" in rendered

    def test_qa_template_renders_with_metadata(self):
        tmpl = QATemplate()
        rendered = tmpl.render(
            content="Some text here.",
            metadata={"title": "Science 101", "num_examples": 5},
        )
        assert "Some text here." in rendered
        assert "Science 101" in rendered
        assert "5" in rendered

    def test_qa_template_has_system_prompt(self):
        tmpl = QATemplate()
        assert isinstance(tmpl.system_prompt, str)
        assert len(tmpl.system_prompt) > 20
        # Should mention JSON or question-answer
        prompt_lower = tmpl.system_prompt.lower()
        assert "question" in prompt_lower or "q&a" in prompt_lower or "qa" in prompt_lower

    def test_qa_template_has_output_schema(self):
        tmpl = QATemplate()
        schema = tmpl.output_schema
        assert isinstance(schema, dict)
        assert "type" in schema


# ---------------------------------------------------------------------------
# Summarization template tests
# ---------------------------------------------------------------------------

class TestSummarizationTemplate:
    def test_summarization_template_renders(self):
        tmpl = SummarizationTemplate()
        rendered = tmpl.render(content="A long article about climate change...")
        assert "A long article about climate change..." in rendered


# ---------------------------------------------------------------------------
# Classification template tests
# ---------------------------------------------------------------------------

class TestClassificationTemplate:
    def test_classification_template_renders_with_labels(self):
        tmpl = ClassificationTemplate()
        rendered = tmpl.render(
            content="Some news article about stocks.",
            metadata={"labels": ["business", "politics", "sports", "technology"]},
        )
        assert "Some news article about stocks." in rendered
        assert "business" in rendered


# ---------------------------------------------------------------------------
# Instruction-following template tests
# ---------------------------------------------------------------------------

class TestInstructionTemplate:
    def test_instruction_template_renders(self):
        tmpl = InstructionTemplate()
        rendered = tmpl.render(content="Detailed tutorial on Python decorators.")
        assert "Detailed tutorial on Python decorators." in rendered


# ---------------------------------------------------------------------------
# Response parsing tests
# ---------------------------------------------------------------------------

class TestParseResponse:
    def test_parse_response_valid_json_array(self):
        tmpl = QATemplate()
        response = json.dumps([
            {"input": "What color is the sky?", "output": "Blue"},
            {"input": "Why?", "output": "Rayleigh scattering"},
        ])
        result = tmpl.parse_response(response)
        assert len(result) == 2
        assert result[0]["input"] == "What color is the sky?"
        assert result[0]["output"] == "Blue"
        assert result[1]["input"] == "Why?"
        assert result[1]["output"] == "Rayleigh scattering"

    def test_parse_response_valid_json_object(self):
        tmpl = QATemplate()
        response = json.dumps({"input": "Single question?", "output": "Single answer."})
        result = tmpl.parse_response(response)
        assert len(result) == 1
        assert result[0]["input"] == "Single question?"
        assert result[0]["output"] == "Single answer."

    def test_parse_response_invalid_json_returns_empty(self):
        tmpl = QATemplate()
        result = tmpl.parse_response("this is not json {{{")
        assert result == []


# ---------------------------------------------------------------------------
# Template type attribute test
# ---------------------------------------------------------------------------

class TestAllTemplatesHaveType:
    def test_all_templates_have_template_type(self):
        expected = {
            "qa": QATemplate,
            "summarization": SummarizationTemplate,
            "classification": ClassificationTemplate,
            "instruction": InstructionTemplate,
        }
        for type_name, cls in expected.items():
            instance = cls()
            assert instance.template_type == type_name, (
                f"{cls.__name__}.template_type should be '{type_name}', got '{instance.template_type}'"
            )
