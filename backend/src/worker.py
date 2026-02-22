"""Worker entry point: consumes jobs from Redis and runs the pipeline."""

from __future__ import annotations

import asyncio
import signal
import sys

from loguru import logger

from clients.llm_client import LLMClient
from clients.redis_client import RedisClient
from config import get_settings
from db.database import init_db, close_db
from logging_config import setup_logging
from pipeline.orchestrator import PipelineOrchestrator


class Worker:
    """Pipeline worker that consumes jobs from a Redis queue."""

    def __init__(self) -> None:
        self._running = True
        self._redis: RedisClient | None = None

    async def start(self) -> None:
        """Initialize services and start the job processing loop."""
        settings = get_settings()
        setup_logging(level=settings.log_level)
        logger.info("Worker starting...")

        # Initialize DB
        await init_db()

        # Import _session_factory after init_db populates it
        from db.database import _session_factory, get_async_session

        # Load custom templates into registry
        from templates import TemplateRegistry
        try:
            async with get_async_session() as session:
                await TemplateRegistry.load_custom_templates(session)
            logger.info("Custom templates loaded into registry")
        except Exception as exc:
            logger.warning(f"Failed to load custom templates: {exc}")

        # Initialize clients
        self._redis = RedisClient()
        llm_client = LLMClient()

        # Build orchestrator
        orchestrator = PipelineOrchestrator(
            session_factory=_session_factory,
            redis_client=self._redis,
            llm_client=llm_client,
        )

        logger.info("Worker ready, waiting for jobs...")

        # Main loop
        while self._running:
            try:
                payload = await self._redis.dequeue_job(timeout=5)
                if payload is None:
                    continue  # timeout, loop back

                job_id = payload.get("job_id")
                if job_id is None:
                    logger.warning(f"Invalid job payload (no job_id): {payload}")
                    continue

                logger.info(f"Processing job {job_id}")
                try:
                    await orchestrator.run(job_id)
                    logger.info(f"Job {job_id} completed successfully")
                except Exception as exc:
                    logger.error(f"Job {job_id} failed: {exc}")

            except asyncio.CancelledError:
                logger.info("Worker cancelled")
                break
            except Exception as exc:
                logger.error(f"Worker loop error: {exc}")
                await asyncio.sleep(1)  # avoid tight error loops

        await self._shutdown()

    async def _shutdown(self) -> None:
        """Clean up resources."""
        logger.info("Worker shutting down...")
        if self._redis:
            await self._redis.close()
        await close_db()
        logger.info("Worker stopped")

    def request_stop(self) -> None:
        """Signal the worker to stop after the current job finishes."""
        logger.info("Shutdown requested")
        self._running = False


def _handle_signal(worker: Worker) -> None:
    """Register signal handlers for graceful shutdown."""
    def handler(sig, frame):
        worker.request_stop()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def main() -> None:
    """Entry point for the worker process."""
    worker = Worker()
    _handle_signal(worker)
    asyncio.run(worker.start())


if __name__ == "__main__":
    main()
