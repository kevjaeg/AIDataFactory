"""Tests for the Pipeline Orchestrator (Task 20)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from db.models import Base, Export, Job
from pipeline.base import StageResult
from pipeline.orchestrator import PipelineOrchestrator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_setup():
    """Create an in-memory async SQLite DB with all tables."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


@pytest.fixture
def redis_mock():
    """Return an AsyncMock RedisClient."""
    mock = AsyncMock()
    mock.publish = AsyncMock()
    return mock


@pytest.fixture
def llm_mock():
    """Return an AsyncMock LLMClient."""
    return AsyncMock()


@pytest.fixture
def job_config():
    """Standard job config used across tests."""
    return {
        "urls": ["https://example.com/page1", "https://example.com/page2"],
        "scraping": {"rate_limit": 1.0, "max_concurrent": 2},
        "processing": {"chunk_size": 256, "chunk_overlap": 25},
        "generation": {"template": "qa", "model": "gpt-4o-mini"},
        "quality": {"min_score": 0.7, "checks": ["toxicity", "readability"]},
        "export": {"format": "jsonl", "version": "v1"},
    }


async def _create_pending_job(
    factory: async_sessionmaker,
    config: dict,
    project_id: int = 1,
) -> int:
    """Insert a pending Job row and return its ID."""
    async with factory() as session:
        job = Job(project_id=project_id, status="pending", config=config)
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job.id


# ---------------------------------------------------------------------------
# Mock stage results
# ---------------------------------------------------------------------------

_SPIDER_RESULT = StageResult(
    success=True,
    data=[
        {
            "url": "https://example.com/page1",
            "html_path": "/tmp/raw/abc.html",
            "status_code": 200,
            "method": "httpx",
            "title": "Page 1",
            "language": "en",
        },
    ],
    stats={"total_urls": 2, "successful": 1, "failed": 1},
)

_REFINER_RESULT = StageResult(
    success=True,
    data=[
        {
            "url": "https://example.com/page1",
            "title": "Page 1",
            "language": "en",
            "content": "Some extracted text...",
            "chunks": [
                {
                    "content": "Chunk text here",
                    "token_count": 50,
                    "chunk_index": 0,
                    "metadata": {"source_url": "https://example.com/page1"},
                },
            ],
        },
    ],
    stats={"total_documents": 1, "processed": 1, "total_chunks": 1},
)

_FACTORY_RESULT = StageResult(
    success=True,
    data=[
        {
            "input": "What is AI?",
            "output": "AI stands for Artificial Intelligence.",
            "template_type": "qa",
            "model_used": "gpt-4o-mini",
            "token_count": 120,
            "cost": 0.0005,
            "source_chunk": "Chunk text here",
            "source_url": "https://example.com/page1",
        },
    ],
    stats={"total_examples": 1, "total_tokens": 120, "total_cost": 0.0005},
)

_INSPECTOR_RESULT = StageResult(
    success=True,
    data=[
        {
            "input": "What is AI?",
            "output": "AI stands for Artificial Intelligence.",
            "template_type": "qa",
            "model_used": "gpt-4o-mini",
            "token_count": 120,
            "cost": 0.0005,
            "source_chunk": "Chunk text here",
            "source_url": "https://example.com/page1",
            "quality_score": 0.9,
            "quality_details": {"toxicity": {"score": 0.99}},
            "passed_qc": True,
        },
    ],
    stats={"total": 1, "passed": 1, "failed": 0},
)

_SHIPPER_RESULT = StageResult(
    success=True,
    data=[
        {
            "input": "What is AI?",
            "output": "AI stands for Artificial Intelligence.",
        },
    ],
    stats={
        "file_path": "/tmp/exports/1/v1.jsonl",
        "record_count": 1,
        "dataset_card_path": None,
        "format": "jsonl",
        "total_filtered_out": 0,
    },
)


def _mock_stage(return_result: StageResult) -> MagicMock:
    """Create a mock stage whose ``process`` returns *return_result*."""
    stage = MagicMock()
    stage.process = AsyncMock(return_value=return_result)
    return stage


def _patch_stages():
    """Return a dict of mock stage objects keyed by stage name."""
    return {
        "spider": _mock_stage(_SPIDER_RESULT),
        "refiner": _mock_stage(_REFINER_RESULT),
        "factory": _mock_stage(_FACTORY_RESULT),
        "inspector": _mock_stage(_INSPECTOR_RESULT),
        "shipper": _mock_stage(_SHIPPER_RESULT),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOrchestratorRunsAllStages:
    """test_orchestrator_runs_all_stages"""

    async def test_all_stages_called_in_order(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """All 5 stages must be called sequentially with the correct input chain."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        # All stages called exactly once
        for name in PipelineOrchestrator.STAGES:
            assert mock_stages[name].process.await_count == 1, (
                f"Stage '{name}' not called exactly once"
            )

        # Spider receives the raw URL list
        spider_input = mock_stages["spider"].process.call_args[0][0]
        assert spider_input == job_config["urls"]

        # Refiner receives Spider output
        refiner_input = mock_stages["refiner"].process.call_args[0][0]
        assert refiner_input == _SPIDER_RESULT.data

        # Factory receives Refiner output
        factory_input = mock_stages["factory"].process.call_args[0][0]
        assert factory_input == _REFINER_RESULT.data

        # Inspector receives Factory output
        inspector_input = mock_stages["inspector"].process.call_args[0][0]
        assert inspector_input == _FACTORY_RESULT.data

        # Shipper receives Inspector output
        shipper_input = mock_stages["shipper"].process.call_args[0][0]
        assert shipper_input == _INSPECTOR_RESULT.data


class TestOrchestratorUpdatesJobStatusToRunning:
    """test_orchestrator_updates_job_status_to_running"""

    async def test_status_set_to_running(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Job status must be 'running' after orchestrator starts, before any stage."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        # Capture status DURING spider stage execution
        captured_statuses: list[str] = []

        original_process = mock_stages["spider"].process

        async def capture_status(*args, **kwargs):
            async with db_setup() as session:
                res = await session.execute(select(Job).where(Job.id == job_id))
                job = res.scalar_one()
                captured_statuses.append(job.status)
            return await original_process(*args, **kwargs)

        mock_stages["spider"].process = AsyncMock(side_effect=capture_status)

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        assert captured_statuses[0] == "running"

    async def test_started_at_set(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """started_at must be populated when job transitions to running."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        async with db_setup() as session:
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one()
            assert job.started_at is not None


class TestOrchestratorUpdatesJobStage:
    """test_orchestrator_updates_job_stage"""

    async def test_stage_updated_before_each_run(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """job.stage should reflect each stage name during execution."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        captured_stages: list[str] = []

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        # Instrument each stage to capture the job.stage at call time
        for stage_name in PipelineOrchestrator.STAGES:
            original = mock_stages[stage_name].process

            async def capture_stage(
                *args, _orig=original, _sn=stage_name, **kwargs
            ):
                async with db_setup() as session:
                    res = await session.execute(
                        select(Job).where(Job.id == job_id)
                    )
                    job = res.scalar_one()
                    captured_stages.append(job.stage)
                return await _orig(*args, **kwargs)

            mock_stages[stage_name].process = AsyncMock(side_effect=capture_stage)

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        assert captured_stages == [
            "spider",
            "refiner",
            "factory",
            "inspector",
            "shipper",
        ]


class TestOrchestratorPublishesProgress:
    """test_orchestrator_publishes_progress"""

    async def test_progress_published_for_each_stage(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Redis publish must be called for every stage + final completion."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        # Collect all publish calls
        calls = redis_mock.publish.call_args_list
        channel = f"pipeline:progress:{job_id}"

        # Should have at least one call per stage (running) + 1 completed
        assert len(calls) >= len(PipelineOrchestrator.STAGES) + 1

        # Verify channel name
        for call in calls:
            assert call[0][0] == channel

        # Check first call is spider/running
        first_data = calls[0][0][1]
        assert first_data["stage"] == "spider"
        assert first_data["status"] == "running"

        # Check last call is completed
        last_data = calls[-1][0][1]
        assert last_data["status"] == "completed"
        assert last_data["progress"] == 1.0

    async def test_progress_values_match_stage(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Each running progress event should carry the correct progress value."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        running_calls = [
            c[0][1]
            for c in redis_mock.publish.call_args_list
            if c[0][1].get("status") == "running"
        ]

        expected = [
            ("spider", 0.1),
            ("refiner", 0.3),
            ("factory", 0.6),
            ("inspector", 0.8),
            ("shipper", 1.0),
        ]
        for data, (stage, progress) in zip(running_calls, expected):
            assert data["stage"] == stage
            assert data["progress"] == pytest.approx(progress)


class TestOrchestratorMarksCompletedOnSuccess:
    """test_orchestrator_marks_completed_on_success"""

    async def test_job_completed(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """On success, job.status must be 'completed' and completed_at must be set."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        async with db_setup() as session:
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one()
            assert job.status == "completed"
            assert job.completed_at is not None
            assert job.progress == pytest.approx(1.0)


class TestOrchestratorMarksFailedOnStageError:
    """test_orchestrator_marks_failed_on_stage_error"""

    async def test_exception_marks_failed(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """If a stage raises an exception, the job must be marked 'failed'."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        # Make refiner raise an exception
        mock_stages["refiner"].process = AsyncMock(
            side_effect=RuntimeError("Refiner exploded")
        )

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        async with db_setup() as session:
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one()
            assert job.status == "failed"
            assert "Refiner exploded" in job.error

    async def test_exception_publishes_failure(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Failure event must be published via Redis when a stage raises."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()
        mock_stages["factory"].process = AsyncMock(
            side_effect=ValueError("Factory broke")
        )

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        # Find the failure publish call
        failure_calls = [
            c[0][1]
            for c in redis_mock.publish.call_args_list
            if c[0][1].get("status") == "failed"
        ]
        assert len(failure_calls) >= 1
        assert "Factory broke" in failure_calls[0]["error"]


class TestOrchestratorMarksFailedOnStageFailure:
    """test_orchestrator_marks_failed_on_stage_failure"""

    async def test_stage_returns_failure(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """If stage returns success=False, job must be marked 'failed'."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        # Inspector returns success=False
        mock_stages["inspector"].process = AsyncMock(
            return_value=StageResult(
                success=False,
                data=[],
                errors=["Quality check infrastructure failed"],
            )
        )

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        async with db_setup() as session:
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one()
            assert job.status == "failed"
            assert "Quality check infrastructure failed" in job.error

    async def test_subsequent_stages_not_called_after_failure(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Stages after the failing one must NOT be called."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        # Spider fails
        mock_stages["spider"].process = AsyncMock(
            return_value=StageResult(
                success=False,
                data=[],
                errors=["No URLs could be scraped"],
            )
        )

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        # Only spider was called; subsequent stages were skipped
        mock_stages["spider"].process.assert_awaited_once()
        mock_stages["refiner"].process.assert_not_awaited()
        mock_stages["factory"].process.assert_not_awaited()
        mock_stages["inspector"].process.assert_not_awaited()
        mock_stages["shipper"].process.assert_not_awaited()


class TestOrchestratorCreatesExportRecord:
    """test_orchestrator_creates_export_record"""

    async def test_export_row_created(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """After shipper completes, an Export row must exist in the DB."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        async with db_setup() as session:
            res = await session.execute(
                select(Export).where(Export.job_id == job_id)
            )
            export = res.scalar_one()
            assert export.job_id == job_id
            assert export.format == "jsonl"
            assert export.record_count == 1
            assert export.version == "v1"
            assert export.file_path == "/tmp/exports/1/v1.jsonl"


class TestOrchestratorAccumulatesCost:
    """test_orchestrator_accumulates_cost"""

    async def test_cost_stored_in_job(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """The total cost from the factory stage must be stored in job.cost_total."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        async with db_setup() as session:
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one()
            assert job.cost_total == pytest.approx(0.0005)

    async def test_cost_zero_when_no_factory_cost(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """If factory stage reports zero cost, job.cost_total should be 0."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        # Factory returns no cost in stats
        mock_stages["factory"].process = AsyncMock(
            return_value=StageResult(
                success=True,
                data=_FACTORY_RESULT.data,
                stats={"total_examples": 1, "total_tokens": 0, "total_cost": 0.0},
            )
        )

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        async with db_setup() as session:
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one()
            assert job.cost_total == pytest.approx(0.0)


class TestOrchestratorJobNotFound:
    """test_orchestrator_job_not_found"""

    async def test_nonexistent_job_raises(self, db_setup, redis_mock, llm_mock):
        """Passing a non-existent job_id must raise ValueError."""
        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with pytest.raises(ValueError, match="not found"):
            await orchestrator.run(99999)


class TestOrchestratorJobWrongStatus:
    """test_orchestrator_job_wrong_status"""

    async def test_non_pending_job_raises(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Only jobs with status 'pending' should be runnable."""
        async with db_setup() as session:
            job = Job(
                project_id=1,
                status="completed",
                config=job_config,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.id

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with pytest.raises(ValueError, match="expected 'pending'"):
            await orchestrator.run(job_id)

    async def test_running_job_raises(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """A job already in 'running' state must not be re-run."""
        async with db_setup() as session:
            job = Job(project_id=1, status="running", config=job_config)
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.id

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with pytest.raises(ValueError, match="expected 'pending'"):
            await orchestrator.run(job_id)


class TestOrchestratorPassesCorrectConfigToStages:
    """test_orchestrator_passes_correct_config_to_stages"""

    async def test_spider_receives_scraping_config(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Spider stage must receive scraping config + job_id."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        spider_config = mock_stages["spider"].process.call_args[0][1]
        assert spider_config["rate_limit"] == 1.0
        assert spider_config["max_concurrent"] == 2
        assert spider_config["job_id"] == job_id

    async def test_refiner_receives_processing_config(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Refiner stage must receive processing config."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        refiner_config = mock_stages["refiner"].process.call_args[0][1]
        assert refiner_config["chunk_size"] == 256
        assert refiner_config["chunk_overlap"] == 25

    async def test_factory_receives_generation_config(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Factory stage must receive generation config."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        factory_config = mock_stages["factory"].process.call_args[0][1]
        assert factory_config["template"] == "qa"
        assert factory_config["model"] == "gpt-4o-mini"

    async def test_inspector_receives_quality_config(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Inspector stage must receive quality config."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        inspector_config = mock_stages["inspector"].process.call_args[0][1]
        assert inspector_config["min_score"] == 0.7
        assert inspector_config["checks"] == ["toxicity", "readability"]

    async def test_shipper_receives_export_config_with_job_id(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """Shipper stage must receive export config + job_id + data_dir."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        shipper_config = mock_stages["shipper"].process.call_args[0][1]
        assert shipper_config["format"] == "jsonl"
        assert shipper_config["version"] == "v1"
        assert shipper_config["job_id"] == job_id
        assert "data_dir" in shipper_config


class TestOrchestratorNoSessionFactory:
    """Orchestrator must error if no session_factory is provided."""

    async def test_no_session_factory_raises(self, redis_mock, llm_mock):
        orchestrator = PipelineOrchestrator(
            session_factory=None,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )
        with pytest.raises(RuntimeError, match="session_factory"):
            await orchestrator.run(1)


class TestOrchestratorNoRedis:
    """Orchestrator should work without Redis (progress publishing is skipped)."""

    async def test_runs_without_redis(self, db_setup, llm_mock, job_config):
        """Pipeline should complete successfully even without a Redis client."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=None,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        async with db_setup() as session:
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one()
            assert job.status == "completed"


class TestOrchestratorCancellationPolling:
    """Cancellation polling stops the pipeline between stages."""

    async def test_cancelled_between_stages(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """If a job is cancelled mid-pipeline, subsequent stages are skipped."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        # After spider completes, cancel the job in DB
        original_spider = mock_stages["spider"].process

        async def spider_then_cancel(*args, **kwargs):
            result = await original_spider(*args, **kwargs)
            async with db_setup() as session:
                res = await session.execute(select(Job).where(Job.id == job_id))
                job = res.scalar_one()
                job.status = "cancelled"
                await session.commit()
            return result

        mock_stages["spider"].process = AsyncMock(side_effect=spider_then_cancel)

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        # Spider ran, but refiner and later stages were skipped
        mock_stages["spider"].process.assert_awaited_once()
        mock_stages["refiner"].process.assert_not_awaited()
        mock_stages["factory"].process.assert_not_awaited()

    async def test_normal_flow_unaffected(
        self, db_setup, redis_mock, llm_mock, job_config
    ):
        """When no cancellation occurs, all stages run normally."""
        job_id = await _create_pending_job(db_setup, job_config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        # All 5 stages were called
        for name in PipelineOrchestrator.STAGES:
            assert mock_stages[name].process.await_count == 1

        async with db_setup() as session:
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one()
            assert job.status == "completed"


class TestOrchestratorCostLimit:
    """Cost limit check stops the pipeline when exceeded."""

    async def test_cost_exceeded_marks_failed(
        self, db_setup, redis_mock, llm_mock
    ):
        """If factory cost exceeds max_cost, job is marked failed."""
        config = {
            "urls": ["https://example.com"],
            "scraping": {},
            "processing": {},
            "generation": {"template": "qa", "model": "gpt-4o-mini"},
            "quality": {},
            "export": {"format": "jsonl"},
            "max_cost": 0.0001,  # Very low limit
        }
        job_id = await _create_pending_job(db_setup, config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        async with db_setup() as session:
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one()
            assert job.status == "failed"
            assert "Cost limit exceeded" in job.error

        # Inspector and shipper should NOT have run
        mock_stages["inspector"].process.assert_not_awaited()
        mock_stages["shipper"].process.assert_not_awaited()

    async def test_cost_within_limit_passes(
        self, db_setup, redis_mock, llm_mock
    ):
        """If factory cost is within max_cost, pipeline continues."""
        config = {
            "urls": ["https://example.com"],
            "scraping": {},
            "processing": {},
            "generation": {"template": "qa", "model": "gpt-4o-mini"},
            "quality": {},
            "export": {"format": "jsonl"},
            "max_cost": 1.0,  # Generous limit
        }
        job_id = await _create_pending_job(db_setup, config)
        mock_stages = _patch_stages()

        orchestrator = PipelineOrchestrator(
            session_factory=db_setup,
            redis_client=redis_mock,
            llm_client=llm_mock,
        )

        with patch.object(orchestrator, "_build_stages", return_value=mock_stages):
            await orchestrator.run(job_id)

        async with db_setup() as session:
            res = await session.execute(select(Job).where(Job.id == job_id))
            job = res.scalar_one()
            assert job.status == "completed"
