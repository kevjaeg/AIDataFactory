"""Pipeline Orchestrator: runs the full pipeline Spider -> Refiner -> Factory -> Inspector -> Shipper."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from clients.llm_client import LLMClient
from clients.redis_client import RedisClient
from config import get_settings
from db.models import Export, Job
from pipeline.base import StageResult
from pipeline.stages.export import ShipperStage
from pipeline.stages.generation import FactoryStage
from pipeline.stages.ingestion import SpiderStage
from pipeline.stages.processing import RefinerStage
from pipeline.stages.quality import InspectorStage


class PipelineOrchestrator:
    """Runs the full pipeline: Spider -> Refiner -> Factory -> Inspector -> Shipper."""

    STAGES = ["spider", "refiner", "factory", "inspector", "shipper"]

    STAGE_PROGRESS: dict[str, float] = {
        "spider": 0.1,
        "refiner": 0.3,
        "factory": 0.6,
        "inspector": 0.8,
        "shipper": 1.0,
    }

    def __init__(
        self,
        session_factory: async_sessionmaker | None = None,
        redis_client: RedisClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis_client
        self._llm_client = llm_client

    # ------------------------------------------------------------------
    # Stage construction
    # ------------------------------------------------------------------

    def _build_stages(self) -> dict[str, Any]:
        """Instantiate all pipeline stages with their dependencies."""
        settings = get_settings()
        return {
            "spider": SpiderStage(data_dir=settings.data_dir),
            "refiner": RefinerStage(),
            "factory": FactoryStage(llm_client=self._llm_client),
            "inspector": InspectorStage(),
            "shipper": ShipperStage(),
        }

    # ------------------------------------------------------------------
    # Config mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _stage_config(stage_name: str, job: Job) -> dict[str, Any]:
        """Extract the per-stage config slice from the job's config dict."""
        config = job.config or {}
        job_id = job.id

        mapping: dict[str, dict[str, Any]] = {
            "spider": {**config.get("scraping", {}), "job_id": job_id},
            "refiner": config.get("processing", {}),
            "factory": config.get("generation", {}),
            "inspector": config.get("quality", {}),
            "shipper": {
                **config.get("export", {}),
                "job_id": job_id,
                "data_dir": str(get_settings().data_dir),
            },
        }
        return mapping.get(stage_name, {})

    # ------------------------------------------------------------------
    # Progress publishing
    # ------------------------------------------------------------------

    async def _publish_progress(
        self,
        job_id: int,
        stage: str,
        progress: float,
        status: str,
        error: str | None = None,
    ) -> None:
        """Publish a progress event via Redis Pub/Sub."""
        if self._redis is None:
            return
        data: dict[str, Any] = {
            "stage": stage,
            "progress": progress,
            "status": status,
        }
        if error is not None:
            data["error"] = error
        try:
            await self._redis.publish(f"pipeline:progress:{job_id}", data)
        except Exception as exc:
            logger.warning(f"Failed to publish progress for job {job_id}: {exc}")

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    async def run(self, job_id: int) -> None:
        """Execute the full pipeline for *job_id*.

        1. Load the job from DB and validate its status.
        2. Run each stage sequentially, updating the job record after each.
        3. On failure, mark the job as ``"failed"`` and store the error.
        4. On success, create an ``Export`` record and mark the job ``"completed"``.
        """
        if self._session_factory is None:
            raise RuntimeError("session_factory is required")

        # --- Load job ---
        async with self._session_factory() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()

        if job is None:
            logger.error(f"Job {job_id} not found")
            raise ValueError(f"Job {job_id} not found")

        if job.status != "pending":
            logger.warning(f"Job {job_id} has status '{job.status}', expected 'pending'")
            raise ValueError(
                f"Job {job_id} has status '{job.status}', expected 'pending'"
            )

        # --- Mark running ---
        async with self._session_factory() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one()
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            await session.commit()

        logger.info(f"Pipeline started for job {job_id}")

        # --- Build stages ---
        stages = self._build_stages()

        # First stage input: URLs from job config
        stage_input: Any = (job.config or {}).get("urls", [])
        total_cost: float = 0.0

        # --- Run each stage ---
        for stage_name in self.STAGES:
            progress = self.STAGE_PROGRESS[stage_name]
            stage_obj = stages[stage_name]
            stage_config = self._stage_config(stage_name, job)

            # Update job stage + publish progress
            async with self._session_factory() as session:
                db_result = await session.execute(select(Job).where(Job.id == job_id))
                job = db_result.scalar_one()
                job.stage = stage_name
                job.progress = progress
                await session.commit()

            await self._publish_progress(job_id, stage_name, progress, "running")
            logger.info(f"Job {job_id}: starting stage '{stage_name}'")

            # Execute stage
            try:
                stage_result: StageResult = await stage_obj.process(stage_input, stage_config)
            except Exception as exc:
                error_msg = f"Stage '{stage_name}' raised an exception: {exc}"
                logger.error(f"Job {job_id}: {error_msg}")
                await self._mark_failed(job_id, error_msg)
                await self._publish_progress(
                    job_id, stage_name, progress, "failed", error=error_msg
                )
                return

            # Check for stage failure
            if not stage_result.success:
                error_msg = (
                    f"Stage '{stage_name}' failed: "
                    + "; ".join(stage_result.errors)
                )
                logger.error(f"Job {job_id}: {error_msg}")
                await self._mark_failed(job_id, error_msg)
                await self._publish_progress(
                    job_id, stage_name, progress, "failed", error=error_msg
                )
                return

            # Accumulate cost from factory stage
            if stage_name == "factory":
                total_cost += stage_result.stats.get("total_cost", 0.0)

            logger.info(
                f"Job {job_id}: stage '{stage_name}' completed "
                f"({len(stage_result.data)} items)"
            )

            # Output of this stage becomes input of the next
            stage_input = stage_result.data

        # --- All stages completed successfully ---

        # Create Export record
        shipper_stats = stage_result.stats  # type: ignore[possibly-undefined]
        async with self._session_factory() as session:
            export = Export(
                job_id=job_id,
                format=shipper_stats.get("format", "jsonl"),
                file_path=shipper_stats.get("file_path", ""),
                record_count=shipper_stats.get("record_count", 0),
                version="v1",
                dataset_card=None,
            )
            # Read dataset card from disk if available
            dataset_card_path = shipper_stats.get("dataset_card_path")
            if dataset_card_path:
                try:
                    from pathlib import Path

                    card_text = Path(dataset_card_path).read_text(encoding="utf-8")
                    export.dataset_card = card_text
                except Exception:
                    pass
            session.add(export)
            await session.commit()

        # Mark job completed
        async with self._session_factory() as session:
            db_result = await session.execute(select(Job).where(Job.id == job_id))
            job = db_result.scalar_one()
            job.status = "completed"
            job.progress = 1.0
            job.cost_total = total_cost
            job.completed_at = datetime.now(timezone.utc)
            await session.commit()

        await self._publish_progress(job_id, "shipper", 1.0, "completed")
        logger.info(f"Pipeline completed for job {job_id} (cost={total_cost:.4f})")

    # ------------------------------------------------------------------
    # Failure helper
    # ------------------------------------------------------------------

    async def _mark_failed(self, job_id: int, error: str) -> None:
        """Set the job status to 'failed' and store the error message."""
        async with self._session_factory() as session:
            db_result = await session.execute(select(Job).where(Job.id == job_id))
            job = db_result.scalar_one()
            job.status = "failed"
            job.error = error
            await session.commit()
