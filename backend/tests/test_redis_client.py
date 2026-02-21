import pytest
from unittest.mock import AsyncMock, patch

from clients.redis_client import RedisClient


async def test_redis_client_publish() -> None:
    client = RedisClient.__new__(RedisClient)
    client._redis = AsyncMock()
    await client.publish("test-channel", {"status": "ok"})
    client._redis.publish.assert_called_once()


async def test_redis_client_enqueue_job() -> None:
    client = RedisClient.__new__(RedisClient)
    client._redis = AsyncMock()
    await client.enqueue_job(job_id=1, config={"urls": ["https://example.com"]})
    client._redis.lpush.assert_called_once()
