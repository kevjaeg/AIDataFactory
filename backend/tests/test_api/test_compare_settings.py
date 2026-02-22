"""Tests for job comparison and settings endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_job(client: AsyncClient) -> int:
    """Helper: create a project + job, return job_id."""
    proj = await client.post("/api/projects", json={"name": "Compare Test"})
    project_id = proj.json()["id"]
    job = await client.post(
        f"/api/projects/{project_id}/jobs",
        json={"urls": ["https://example.com"]},
    )
    return job.json()["id"]


# ---------------------------------------------------------------------------
# Job Comparison tests
# ---------------------------------------------------------------------------


async def test_compare_jobs_success(client: AsyncClient) -> None:
    """Compare 2 jobs returns valid comparison data."""
    job1 = await _create_job(client)
    job2 = await _create_job(client)

    response = await client.get(f"/api/jobs/compare?ids={job1},{job2}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) == 2
    assert data["jobs"][0]["job_id"] == job1
    assert data["jobs"][1]["job_id"] == job2
    # No examples yet, so all stats should be 0
    assert data["jobs"][0]["total_examples"] == 0
    assert data["jobs"][0]["pass_rate"] == 0.0


async def test_compare_jobs_too_few(client: AsyncClient) -> None:
    """Comparing fewer than 2 jobs returns 400."""
    job1 = await _create_job(client)
    response = await client.get(f"/api/jobs/compare?ids={job1}")
    assert response.status_code == 400
    assert "At least 2" in response.json()["detail"]


async def test_compare_jobs_invalid_ids(client: AsyncClient) -> None:
    """Invalid job IDs format returns 400."""
    response = await client.get("/api/jobs/compare?ids=abc,def")
    assert response.status_code == 400


async def test_compare_jobs_not_found(client: AsyncClient) -> None:
    """Non-existent job ID returns 404."""
    response = await client.get("/api/jobs/compare?ids=99998,99999")
    assert response.status_code == 404


async def test_compare_route_before_job_id(client: AsyncClient) -> None:
    """Verify /api/jobs/compare doesn't match as a job_id."""
    # This should hit the compare endpoint, not the get_job endpoint
    response = await client.get("/api/jobs/compare?ids=1,2")
    # Should be 404 (job not found) not a validation error for job_id
    assert response.status_code in (200, 404)
    # It should NOT be 422 (which would mean "compare" was parsed as job_id)
    assert response.status_code != 422


# ---------------------------------------------------------------------------
# Settings tests
# ---------------------------------------------------------------------------


async def test_get_settings(client: AsyncClient) -> None:
    """Settings endpoint returns config with masked keys."""
    response = await client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert "generation_model" in data
    assert "quality_min_score" in data
    assert "quality_checks" in data
    assert "processing_chunk_size" in data
    assert "export_format" in data

    # Keys should be boolean flags, not actual values
    assert isinstance(data["openai_api_key_configured"], bool)
    assert isinstance(data["huggingface_token_configured"], bool)

    # Default values should be present
    assert data["generation_model"] == "gpt-4o-mini"
    assert data["quality_min_score"] == 0.7
    assert data["export_format"] == "jsonl"
    assert data["processing_chunk_size"] == 512
