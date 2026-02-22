"""Tests for the SSE streaming endpoint."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from api.routes.stream import _event_generator, KEEPALIVE_INTERVAL
from main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redis_message(data: dict) -> dict:
    """Format a Redis pub/sub message dict."""
    return {"type": "message", "data": json.dumps(data)}


def _make_mock_pubsub(messages: list[dict | None]):
    """Create a mock PubSub that returns messages from a list, then blocks.

    Once all pre-loaded messages have been consumed, subsequent calls to
    ``get_message`` will raise ``asyncio.TimeoutError`` (simulating the
    keepalive timeout path).
    """
    pubsub = AsyncMock()
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.aclose = AsyncMock()

    call_count = 0

    async def get_message(ignore_subscribe_messages=True):
        nonlocal call_count
        if call_count < len(messages):
            msg = messages[call_count]
            call_count += 1
            return msg
        # After all messages consumed, simulate timeout
        raise asyncio.TimeoutError

    pubsub.get_message = AsyncMock(side_effect=get_message)
    return pubsub


def _make_mock_redis(pubsub):
    """Return a mock redis instance whose .pubsub() returns *pubsub*.

    ``pubsub()`` on the real redis client is a **synchronous** method,
    so we use ``MagicMock`` for the redis object to avoid coroutine issues.
    """
    mock_redis = MagicMock()
    mock_redis.pubsub.return_value = pubsub
    mock_redis.aclose = AsyncMock()
    return mock_redis


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_event_generator_yields_sse_events():
    """Two running events + one completed event are yielded in SSE format."""
    messages = [
        _redis_message({"stage": "spider", "progress": 0.25, "status": "running"}),
        _redis_message({"stage": "refiner", "progress": 0.50, "status": "running"}),
        _redis_message({"stage": "shipper", "progress": 1.0, "status": "completed"}),
    ]
    pubsub = _make_mock_pubsub(messages)
    mock_redis = _make_mock_redis(pubsub)

    with patch("api.routes.stream.aioredis") as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        events = [ev async for ev in _event_generator(42)]

    assert len(events) == 3
    for ev in events:
        assert ev.startswith("data: ")
        assert ev.endswith("\n\n")


@pytest.mark.asyncio
async def test_event_generator_stops_on_completed():
    """Generator stops iterating once it sees status=completed."""
    messages = [
        _redis_message({"stage": "spider", "progress": 0.5, "status": "running"}),
        _redis_message({"stage": "shipper", "progress": 1.0, "status": "completed"}),
        # This should never be reached:
        _redis_message({"stage": "extra", "progress": 1.0, "status": "running"}),
    ]
    pubsub = _make_mock_pubsub(messages)
    mock_redis = _make_mock_redis(pubsub)

    with patch("api.routes.stream.aioredis") as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        events = [ev async for ev in _event_generator(1)]

    # Only 2 events; the third message is never consumed.
    assert len(events) == 2
    parsed_last = json.loads(events[-1].removeprefix("data: ").strip())
    assert parsed_last["status"] == "completed"


@pytest.mark.asyncio
async def test_event_generator_stops_on_failed():
    """Generator stops iterating once it sees status=failed."""
    messages = [
        _redis_message({"stage": "spider", "progress": 0.1, "status": "running"}),
        _redis_message({"stage": "spider", "progress": 0.1, "status": "failed"}),
    ]
    pubsub = _make_mock_pubsub(messages)
    mock_redis = _make_mock_redis(pubsub)

    with patch("api.routes.stream.aioredis") as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        events = [ev async for ev in _event_generator(7)]

    assert len(events) == 2
    parsed_last = json.loads(events[-1].removeprefix("data: ").strip())
    assert parsed_last["status"] == "failed"


@pytest.mark.asyncio
async def test_event_generator_keepalive():
    """A keepalive comment is emitted when get_message times out."""
    # No real messages -- the mock will immediately raise TimeoutError
    pubsub = _make_mock_pubsub([])
    mock_redis = _make_mock_redis(pubsub)

    with patch("api.routes.stream.aioredis") as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis

        events: list[str] = []
        async for ev in _event_generator(99):
            events.append(ev)
            if len(events) >= 2:
                # We got 2 keepalives, that's enough to verify
                break

    assert all(ev == ": keepalive\n\n" for ev in events)


@pytest.mark.asyncio
async def test_stream_endpoint_returns_streaming_response():
    """GET /api/jobs/{job_id}/stream returns 200 with text/event-stream."""
    messages = [
        _redis_message({"stage": "spider", "progress": 1.0, "status": "completed"}),
    ]
    pubsub = _make_mock_pubsub(messages)
    mock_redis = _make_mock_redis(pubsub)

    with patch("api.routes.stream.aioredis") as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/jobs/1/stream")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert response.text.startswith("data: ")


@pytest.mark.asyncio
async def test_event_generator_handles_invalid_json():
    """Non-JSON message data is yielded without crashing the generator."""
    messages = [
        {"type": "message", "data": "not-valid-json!!!"},
        _redis_message({"status": "completed"}),
    ]
    pubsub = _make_mock_pubsub(messages)
    mock_redis = _make_mock_redis(pubsub)

    with patch("api.routes.stream.aioredis") as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        events = [ev async for ev in _event_generator(5)]

    # Both messages emitted; first one is non-JSON but still yielded
    assert len(events) == 2
    assert "not-valid-json!!!" in events[0]


@pytest.mark.asyncio
async def test_event_generator_subscribes_to_correct_channel():
    """pubsub.subscribe is called with pipeline:progress:{job_id}."""
    messages = [
        _redis_message({"status": "completed"}),
    ]
    pubsub = _make_mock_pubsub(messages)
    mock_redis = _make_mock_redis(pubsub)

    with patch("api.routes.stream.aioredis") as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        _ = [ev async for ev in _event_generator(123)]

    pubsub.subscribe.assert_awaited_once_with("pipeline:progress:123")


@pytest.mark.asyncio
async def test_event_generator_cleanup():
    """unsubscribe and aclose are called even after normal completion."""
    messages = [
        _redis_message({"status": "completed"}),
    ]
    pubsub = _make_mock_pubsub(messages)
    mock_redis = _make_mock_redis(pubsub)

    with patch("api.routes.stream.aioredis") as mock_aioredis:
        mock_aioredis.from_url.return_value = mock_redis
        _ = [ev async for ev in _event_generator(10)]

    pubsub.unsubscribe.assert_awaited_once_with("pipeline:progress:10")
    pubsub.aclose.assert_awaited_once()
    mock_redis.aclose.assert_awaited_once()
