import pytest
from httpx import AsyncClient


async def test_create_job(client: AsyncClient) -> None:
    # First create a project
    project_resp = await client.post("/api/projects", json={"name": "Job Test Project"})
    project_id = project_resp.json()["id"]

    # Create a job
    response = await client.post(f"/api/projects/{project_id}/jobs", json={
        "urls": ["https://example.com/article-1", "https://example.com/article-2"],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == project_id
    assert data["status"] == "pending"
    assert data["config"] is not None
    assert data["progress"] == 0.0


async def test_create_job_with_custom_config(client: AsyncClient) -> None:
    project_resp = await client.post("/api/projects", json={"name": "Custom Config"})
    project_id = project_resp.json()["id"]

    response = await client.post(f"/api/projects/{project_id}/jobs", json={
        "urls": ["https://example.com"],
        "config": {
            "generation": {"template": "summarization", "model": "gpt-4o"},
            "quality": {"min_score": 0.8},
        }
    })
    assert response.status_code == 201
    data = response.json()
    config = data["config"]
    assert config["generation"]["template"] == "summarization"
    assert config["quality"]["min_score"] == 0.8
    # Defaults should be filled in
    assert config["scraping"]["max_concurrent"] == 3


async def test_create_job_nonexistent_project(client: AsyncClient) -> None:
    response = await client.post("/api/projects/99999/jobs", json={
        "urls": ["https://example.com"],
    })
    assert response.status_code == 404


async def test_list_jobs_for_project(client: AsyncClient) -> None:
    project_resp = await client.post("/api/projects", json={"name": "List Jobs"})
    project_id = project_resp.json()["id"]

    await client.post(f"/api/projects/{project_id}/jobs", json={"urls": ["https://a.com"]})
    await client.post(f"/api/projects/{project_id}/jobs", json={"urls": ["https://b.com"]})

    response = await client.get(f"/api/projects/{project_id}/jobs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_get_job_detail(client: AsyncClient) -> None:
    project_resp = await client.post("/api/projects", json={"name": "Detail"})
    project_id = project_resp.json()["id"]

    job_resp = await client.post(f"/api/projects/{project_id}/jobs", json={
        "urls": ["https://example.com"],
    })
    job_id = job_resp.json()["id"]

    response = await client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["id"] == job_id


async def test_get_nonexistent_job(client: AsyncClient) -> None:
    response = await client.get("/api/jobs/99999")
    assert response.status_code == 404


async def test_cancel_job(client: AsyncClient) -> None:
    project_resp = await client.post("/api/projects", json={"name": "Cancel"})
    project_id = project_resp.json()["id"]

    job_resp = await client.post(f"/api/projects/{project_id}/jobs", json={
        "urls": ["https://example.com"],
    })
    job_id = job_resp.json()["id"]

    response = await client.post(f"/api/jobs/{job_id}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


# ------------------------------------------------------------------
# Retry endpoint tests
# ------------------------------------------------------------------


async def test_retry_failed_job(client: AsyncClient) -> None:
    """Retrying a failed job creates a new pending job with the same config."""
    project_resp = await client.post("/api/projects", json={"name": "Retry"})
    project_id = project_resp.json()["id"]

    job_resp = await client.post(f"/api/projects/{project_id}/jobs", json={
        "urls": ["https://example.com/retry"],
    })
    job_id = job_resp.json()["id"]

    # Cancel first to get it into a retryable state
    await client.post(f"/api/jobs/{job_id}/cancel")

    response = await client.post(f"/api/jobs/{job_id}/retry")
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["project_id"] == project_id
    assert data["id"] != job_id
    assert "https://example.com/retry" in data["config"]["urls"]


async def test_retry_cancelled_job(client: AsyncClient) -> None:
    """Cancelled jobs should also be retryable."""
    project_resp = await client.post("/api/projects", json={"name": "RetryCancelled"})
    project_id = project_resp.json()["id"]

    job_resp = await client.post(f"/api/projects/{project_id}/jobs", json={
        "urls": ["https://example.com"],
    })
    job_id = job_resp.json()["id"]
    await client.post(f"/api/jobs/{job_id}/cancel")

    response = await client.post(f"/api/jobs/{job_id}/retry")
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


async def test_retry_completed_job_rejected(client: AsyncClient) -> None:
    """Completed (non-failed) jobs cannot be retried."""
    project_resp = await client.post("/api/projects", json={"name": "NoRetry"})
    project_id = project_resp.json()["id"]

    job_resp = await client.post(f"/api/projects/{project_id}/jobs", json={
        "urls": ["https://example.com"],
    })
    job_id = job_resp.json()["id"]

    # pending → not failed/cancelled, so retry should be rejected
    response = await client.post(f"/api/jobs/{job_id}/retry")
    assert response.status_code == 400


async def test_retry_nonexistent_job(client: AsyncClient) -> None:
    """Retrying a non-existent job returns 404."""
    response = await client.post("/api/jobs/99999/retry")
    assert response.status_code == 404
