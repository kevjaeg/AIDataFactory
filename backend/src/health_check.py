"""Lightweight Redis ping script for worker container healthcheck."""

import asyncio
import sys

from clients.redis_client import RedisClient


async def check() -> bool:
    try:
        rc = RedisClient()
        ok = await rc.ping()
        await rc.close()
        return ok
    except Exception:
        return False


if __name__ == "__main__":
    ok = asyncio.run(check())
    sys.exit(0 if ok else 1)
