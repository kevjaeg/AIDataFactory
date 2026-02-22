from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import JobCreate, JobResponse, JobComparison, JobComparisonItem
from clients.redis_client import RedisClient
from db.database import get_session
from db.models import Job, Project, TrainingExample

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

    # Enqueue job to Redis for worker processing
    try:
        rc = RedisClient()
        await rc.enqueue_job(job.id, config_dict)
        await rc.close()
    except Exception as exc:
        logger.warning(f"Failed to enqueue job {job.id}: {exc}")

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


@router.get("/api/jobs/compare", response_model=JobComparison)
async def compare_jobs(
    ids: str = Query(..., description="Comma-separated job IDs to compare"),
    session: AsyncSession = Depends(get_session),
) -> JobComparison:
    """Compare quality metrics across multiple jobs."""
    try:
        job_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job IDs format. Use comma-separated integers.")

    if len(job_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 job IDs required for comparison")
    if len(job_ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 jobs can be compared at once")

    items = []
    for jid in job_ids:
        job = await session.get(Job, jid)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {jid} not found")

        # Get example statistics
        total_result = await session.execute(
            select(func.count()).where(TrainingExample.job_id == jid)
        )
        total_examples = total_result.scalar() or 0

        passed_result = await session.execute(
            select(func.count()).where(
                TrainingExample.job_id == jid,
                TrainingExample.passed_qc == True,
            )
        )
        passed_examples = passed_result.scalar() or 0

        avg_score_result = await session.execute(
            select(func.avg(TrainingExample.quality_score)).where(
                TrainingExample.job_id == jid
            )
        )
        avg_quality_score = avg_score_result.scalar() or 0.0

        # Get template type from job config
        template_type = None
        if job.config and isinstance(job.config, dict):
            gen_config = job.config.get("generation", {})
            if isinstance(gen_config, dict):
                template_type = gen_config.get("template")

        failed_examples = total_examples - passed_examples
        pass_rate = passed_examples / total_examples if total_examples > 0 else 0.0

        items.append(JobComparisonItem(
            job_id=jid,
            status=job.status,
            template_type=template_type,
            total_examples=total_examples,
            passed_examples=passed_examples,
            failed_examples=failed_examples,
            avg_quality_score=round(avg_quality_score, 4),
            cost_total=job.cost_total,
            pass_rate=round(pass_rate, 4),
        ))

    return JobComparison(jobs=items)


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
