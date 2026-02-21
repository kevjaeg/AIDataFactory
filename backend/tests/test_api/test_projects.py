import pytest
from httpx import AsyncClient


async def test_create_project(client: AsyncClient) -> None:
    response = await client.post("/api/projects", json={
        "name": "Test Project",
        "description": "A test project",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["id"] is not None


async def test_list_projects(client: AsyncClient) -> None:
    await client.post("/api/projects", json={"name": "Project 1"})
    await client.post("/api/projects", json={"name": "Project 2"})

    response = await client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


async def test_get_project(client: AsyncClient) -> None:
    create = await client.post("/api/projects", json={"name": "Get Me"})
    project_id = create.json()["id"]

    response = await client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Get Me"


async def test_get_nonexistent_project(client: AsyncClient) -> None:
    response = await client.get("/api/projects/99999")
    assert response.status_code == 404


async def test_delete_project(client: AsyncClient) -> None:
    create = await client.post("/api/projects", json={"name": "Delete Me"})
    project_id = create.json()["id"]

    response = await client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204

    response = await client.get(f"/api/projects/{project_id}")
    assert response.status_code == 404
