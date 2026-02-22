"""Stats API routes for dashboard data."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import StatsOverview
from db.database import get_session
from db.models import Job, Project, TrainingExample

router = APIRouter(tags=["stats"])


@router.get("/api/stats/overview", response_model=StatsOverview)
async def get_overview(
    session: AsyncSession = Depends(get_session),
) -> StatsOverview:
    """Return aggregate stats for the dashboard."""
    total_projects = await session.scalar(
        select(func.count()).select_from(Project)
    ) or 0

    total_jobs = await session.scalar(
        select(func.count()).select_from(Job)
    ) or 0

    active_jobs = await session.scalar(
        select(func.count()).select_from(Job).where(
            Job.status.in_(["pending", "running"])
        )
    ) or 0

    total_examples = await session.scalar(
        select(func.count()).select_from(TrainingExample)
    ) or 0

    total_cost = await session.scalar(
        select(func.coalesce(func.sum(Job.cost_total), 0.0))
    ) or 0.0

    return StatsOverview(
        total_projects=total_projects,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_examples=total_examples,
        total_cost=float(total_cost),
    )


@router.get("/api/stats/costs")
async def get_costs(
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Return recent jobs with their cost breakdown."""
    result = await session.execute(
        select(Job)
        .where(Job.status == "completed")
        .order_by(Job.completed_at.desc())
        .limit(limit)
    )
    jobs = result.scalars().all()

    return [
        {
            "job_id": job.id,
            "project_id": job.project_id,
            "cost_total": job.cost_total,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
        for job in jobs
    ]
