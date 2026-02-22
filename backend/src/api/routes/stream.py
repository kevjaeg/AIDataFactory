"""SSE streaming endpoint for real-time job progress."""

from __future__ import annotations

import asyncio
import json

import redis.asyncio as aioredis
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger

from config import get_settings

router = APIRouter(tags=["stream"])

KEEPALIVE_INTERVAL = 15  # seconds


@router.get("/api/jobs/{job_id}/stream")
async def stream_job_progress(job_id: int) -> StreamingResponse:
    """Stream real-time progress events for a pipeline job via SSE."""
    return StreamingResponse(
        _event_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _event_generator(job_id: int):
    """Async generator that yields SSE events from Redis Pub/Sub."""
    settings = get_settings()
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    channel = f"pipeline:progress:{job_id}"

    try:
        await pubsub.subscribe(channel)
        logger.info(f"SSE: subscribed to {channel}")

        while True:
            try:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=KEEPALIVE_INTERVAL,
                )
            except asyncio.TimeoutError:
                # Send keepalive ping
                yield ": keepalive\n\n"
                continue

            if message is None:
                # No message yet, small sleep to avoid busy loop
                await asyncio.sleep(0.1)
                continue

            if message["type"] == "message":
                data = message["data"]
                yield f"data: {data}\n\n"

                # Check if job is completed or failed -- close stream
                try:
                    parsed = json.loads(data)
                    if parsed.get("status") in ("completed", "failed"):
                        logger.info(f"SSE: job {job_id} {parsed['status']}, closing stream")
                        break
                except (json.JSONDecodeError, KeyError):
                    pass

    except asyncio.CancelledError:
        logger.info(f"SSE: client disconnected from {channel}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await r.aclose()
