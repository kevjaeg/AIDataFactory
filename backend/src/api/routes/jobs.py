from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import JobCreate, JobResponse
from db.database import get_session
from db.models import Job, Project

router = APIRouter(tags=["jobs"])


@router.post("/api/projects/{project_id}/jobs", status_code=201, response_model=JobResponse)
async def create_job(
    project_id: int,
    body: JobCreate,
    session: AsyncSession = Depends(get_session),
) -> Job:
    # Verify project exists
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Store the full config as dict (with defaults filled in by Pydantic)
    config_dict = body.config.model_dump()
    config_dict["urls"] = body.urls

    job = Job(
        project_id=project_id,
        status="pending",
        config=config_dict,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # NOTE: In the full system, we'd enqueue to Redis here.
    # For now, just create the DB record.

    return job


@router.get("/api/projects/{project_id}/jobs", response_model=list[JobResponse])
async def list_jobs(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[Job]:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await session.execute(
        select(Job).where(Job.project_id == project_id).order_by(Job.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> Job:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/api/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> Job:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {job.status}")

    job.status = "cancelled"
    await session.commit()
    await session.refresh(job)
    return job
