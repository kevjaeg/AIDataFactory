import pytest
from api.schemas import JobCreate, PipelineConfig, ProjectCreate


def test_job_create_minimal() -> None:
    job = JobCreate(urls=["https://example.com"])
    assert job.config.scraping.max_concurrent == 3
    assert job.config.generation.model == "gpt-4o-mini"
    assert job.config.quality.min_score == 0.7


def test_job_create_custom_config() -> None:
    job = JobCreate(
        urls=["https://example.com"],
        config=PipelineConfig(
            generation={"template": "summarization", "model": "gpt-4o"},
        ),
    )
    assert job.config.generation.template == "summarization"
    assert job.config.generation.model == "gpt-4o"
    assert job.config.scraping.max_concurrent == 3


def test_project_create_validation() -> None:
    project = ProjectCreate(name="My Project", description="Test")
    assert project.name == "My Project"


def test_job_create_requires_urls() -> None:
    with pytest.raises(Exception):
        JobCreate(urls=[])
