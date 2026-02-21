import json

import redis.asyncio as redis
from loguru import logger

from config import get_settings


class RedisClient:
    """Async Redis client for job queue and pub/sub."""

    def __init__(self) -> None:
        settings = get_settings()
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def ping(self) -> bool:
        """Check Redis connection."""
        try:
            return await self._redis.ping()
        except redis.ConnectionError:
            return False

    async def enqueue_job(self, job_id: int, config: dict) -> None:
        """Push a job onto the pipeline queue."""
        payload = json.dumps({"job_id": job_id, "config": config})
        await self._redis.lpush("pipeline:jobs", payload)
        logger.info(f"Enqueued job {job_id}")

    async def dequeue_job(self, timeout: int = 0) -> dict | None:
        """Pop a job from the pipeline queue. Blocks for `timeout` seconds."""
        result = await self._redis.brpop("pipeline:jobs", timeout=timeout)
        if result:
            _, payload = result
            return json.loads(payload)
        return None

    async def publish(self, channel: str, data: dict) -> None:
        """Publish progress update to a channel."""
        await self._redis.publish(channel, json.dumps(data))

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.close()
