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
