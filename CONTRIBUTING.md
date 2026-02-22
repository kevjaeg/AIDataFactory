# Contributing to AI Data Factory

## Development Setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,pipeline]"
playwright install chromium

# Frontend
cd frontend
npm install
```

## Running Tests

```bash
cd backend
pytest                    # all tests
pytest tests/test_api/    # API tests only
pytest tests/test_pipeline/  # pipeline tests only
pytest -v                 # verbose output
```

## Adding a Custom Prompt Template

Templates live in `backend/src/templates/`. Each template is a Python class that extends `BaseTemplate`.

### 1. Create the template file

```python
# backend/src/templates/my_template.py
from templates.base import BaseTemplate

class MyTemplate(BaseTemplate):
    template_type = "my_template"
    description = "Generates custom training examples"
    system_prompt = "You are an expert at creating training data."

    # Jinja2 template for the user prompt
    user_template = """Given the following text, generate {{ n_examples }} training examples.

Text:
{{ chunk }}

Output as JSON array with objects containing "input" and "output" fields."""

    output_format = {
        "input": "The input text or question",
        "output": "The expected model response",
    }
```

### 2. Register it

Add your template to `backend/src/templates/__init__.py`:

```python
from templates.my_template import MyTemplate

TEMPLATE_REGISTRY = {
    # ... existing templates ...
    "my_template": MyTemplate,
}
```

### 3. Use it

When creating a job, specify your template in the config:

```json
{
  "urls": ["https://example.com"],
  "config": {
    "generation": {
      "template_type": "my_template"
    }
  }
}
```

## Adding a Quality Checker

Quality checkers live in `backend/src/pipeline/quality_checks/`. Each checker implements the `QualityChecker` abstract class.

### 1. Create the checker

```python
# backend/src/pipeline/quality_checks/my_checker.py
from pipeline.quality_checks import QualityChecker

class MyChecker(QualityChecker):
    name = "my_check"

    async def check(self, example: dict, **kwargs) -> tuple[float, str]:
        """Return (score, detail) where score is 0.0-1.0."""
        # Your quality check logic here
        score = 1.0
        detail = "passed"
        return score, detail
```

### 2. Register it

Add your checker to the `CHECKER_REGISTRY` in `backend/src/pipeline/stages/quality.py`:

```python
from pipeline.quality_checks.my_checker import MyChecker

CHECKER_REGISTRY = {
    # ... existing checkers ...
    "my_check": MyChecker,
}
```

### 3. Enable it

Add the checker name to the quality checks config:

```json
{
  "config": {
    "quality": {
      "checks": ["toxicity", "readability", "format", "my_check"],
      "weights": {"my_check": 1.5}
    }
  }
}
```

## Code Style

- Python: Ruff formatter, line length 100, Python 3.12+ features
- TypeScript: ESLint + Prettier via Next.js defaults
- Commit messages: `type: description` (feat, fix, docs, refactor, test)

## Architecture Notes

- Pipeline stages don't write to DB directly — the Orchestrator handles persistence
- All LLM calls go through `LLMClient` wrapper (cost tracking, retry logic)
- Redis is used for both job queue (list-based) and progress pub/sub
- Frontend fetches from the backend API at `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`)
