"""Tests for stats and templates API routes."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from db.models import Job, Project, TrainingExample


# ---------------------------------------------------------------------------
# Stats overview tests
# ---------------------------------------------------------------------------


async def test_overview_empty_db(client: AsyncClient) -> None:
    """Fresh DB returns all zeros."""
    response = await client.get("/api/stats/overview")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "total_projects": 0,
        "total_jobs": 0,
        "active_jobs": 0,
        "total_examples": 0,
        "total_cost": 0.0,
    }


async def test_overview_with_data(
    client: AsyncClient,
    session_factory: async_sessionmaker,
) -> None:
    """Insert projects, jobs, examples and verify counts."""
    async with session_factory() as session:
        p1 = Project(name="P1")
        p2 = Project(name="P2")
        session.add_all([p1, p2])
        await session.flush()

        j1 = Job(project_id=p1.id, status="completed", config={}, cost_total=1.5)
        j2 = Job(project_id=p2.id, status="pending", config={}, cost_total=0.0)
        session.add_all([j1, j2])
        await session.flush()

        ex1 = TrainingExample(
            chunk_id=1, job_id=j1.id, template_type="qa",
            input_text="q", output_text="a", model_used="gpt-4o-mini",
        )
        ex2 = TrainingExample(
            chunk_id=2, job_id=j1.id, template_type="qa",
            input_text="q2", output_text="a2", model_used="gpt-4o-mini",
        )
        session.add_all([ex1, ex2])
        await session.commit()

    response = await client.get("/api/stats/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_projects"] == 2
    assert data["total_jobs"] == 2
    assert data["active_jobs"] == 1  # only pending
    assert data["total_examples"] == 2
    assert data["total_cost"] == 1.5


async def test_overview_active_jobs_counts_pending_and_running(
    client: AsyncClient,
    session_factory: async_sessionmaker,
) -> None:
    """Only pending and running count as active."""
    async with session_factory() as session:
        p = Project(name="Active")
        session.add(p)
        await session.flush()

        statuses = ["pending", "running", "completed", "failed", "cancelled"]
        for s in statuses:
            session.add(Job(project_id=p.id, status=s, config={}))
        await session.commit()

    response = await client.get("/api/stats/overview")
    data = response.json()
    assert data["total_jobs"] == 5
    assert data["active_jobs"] == 2  # pending + running


async def test_overview_total_cost(
    client: AsyncClient,
    session_factory: async_sessionmaker,
) -> None:
    """Total cost sums all job cost_total values."""
    async with session_factory() as session:
        p = Project(name="Cost")
        session.add(p)
        await session.flush()

        session.add(Job(project_id=p.id, status="completed", config={}, cost_total=2.50))
        session.add(Job(project_id=p.id, status="completed", config={}, cost_total=3.75))
        session.add(Job(project_id=p.id, status="failed", config={}, cost_total=0.10))
        await session.commit()

    response = await client.get("/api/stats/overview")
    data = response.json()
    assert abs(data["total_cost"] - 6.35) < 0.01


# ---------------------------------------------------------------------------
# Stats costs tests
# ---------------------------------------------------------------------------


async def test_costs_returns_completed_jobs(
    client: AsyncClient,
    session_factory: async_sessionmaker,
) -> None:
    """Only completed jobs appear in cost breakdown."""
    async with session_factory() as session:
        p = Project(name="Costs")
        session.add(p)
        await session.flush()

        session.add(Job(
            project_id=p.id, status="completed", config={},
            cost_total=1.0, completed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ))
        session.add(Job(
            project_id=p.id, status="pending", config={}, cost_total=0.0,
        ))
        await session.commit()

    response = await client.get("/api/stats/costs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["cost_total"] == 1.0
    assert data[0]["completed_at"] is not None


async def test_costs_empty(client: AsyncClient) -> None:
    """No completed jobs returns empty list."""
    response = await client.get("/api/stats/costs")
    assert response.status_code == 200
    assert response.json() == []


async def test_costs_limit(
    client: AsyncClient,
    session_factory: async_sessionmaker,
) -> None:
    """Limit parameter restricts the number of returned jobs."""
    async with session_factory() as session:
        p = Project(name="Limit")
        session.add(p)
        await session.flush()

        for i in range(5):
            session.add(Job(
                project_id=p.id, status="completed", config={},
                cost_total=float(i), completed_at=datetime(2026, 1, i + 1, tzinfo=timezone.utc),
            ))
        await session.commit()

    response = await client.get("/api/stats/costs?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


# ---------------------------------------------------------------------------
# Templates tests
# ---------------------------------------------------------------------------


async def test_list_templates(client: AsyncClient) -> None:
    """Returns at least the 4 built-in templates."""
    response = await client.get("/api/templates")
    assert response.status_code == 200
    data = response.json()
    names = {t["name"] for t in data}
    assert {"qa", "summarization", "classification", "instruction"} <= names
    # Each entry should have expected keys
    for entry in data:
        assert "name" in entry
        assert "template_type" in entry
        assert "has_system_prompt" in entry


async def test_get_template_detail(client: AsyncClient) -> None:
    """Returns template details with system_prompt and output_schema."""
    response = await client.get("/api/templates/qa")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "qa"
    assert data["template_type"] == "qa"
    assert isinstance(data["system_prompt"], str)
    assert len(data["system_prompt"]) > 0
    assert isinstance(data["output_schema"], dict)


async def test_get_template_not_found(client: AsyncClient) -> None:
    """404 for unknown template type."""
    response = await client.get("/api/templates/nonexistent_type")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
