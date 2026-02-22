import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from db.models import Base, Project, Job, RawDocument, Chunk, TrainingExample, Export, CustomTemplate


@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s


async def test_all_tables_created(engine) -> None:
    async with engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
    expected = {"projects", "jobs", "raw_documents", "chunks", "training_examples", "exports", "custom_templates"}
    assert expected == set(tables)


async def test_create_project(session: AsyncSession) -> None:
    project = Project(name="Test Project", description="A test")
    session.add(project)
    await session.commit()
    await session.refresh(project)
    assert project.id is not None
    assert project.name == "Test Project"
    assert project.created_at is not None


async def test_create_job_for_project(session: AsyncSession) -> None:
    project = Project(name="Test")
    session.add(project)
    await session.commit()
    await session.refresh(project)

    job = Job(project_id=project.id, status="pending", config={"urls": ["https://example.com"]})
    session.add(job)
    await session.commit()
    await session.refresh(job)
    assert job.id is not None
    assert job.status == "pending"
    assert job.project_id == project.id
