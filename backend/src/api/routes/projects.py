from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from db.database import get_session
from db.models import Project

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", status_code=201, response_model=ProjectResponse)
async def create_project(
    body: ProjectCreate,
    session: AsyncSession = Depends(get_session),
) -> Project:
    project = Project(**body.model_dump())
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
) -> list[Project]:
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> Project:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
) -> Project:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await session.delete(project)
    await session.commit()
    return Response(status_code=204)
