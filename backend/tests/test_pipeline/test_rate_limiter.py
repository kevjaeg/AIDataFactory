import asyncio
import time
import pytest

from pipeline.rate_limiter import RateLimiter


async def test_rate_limiter_allows_first_request_immediately() -> None:
    limiter = RateLimiter(rate_per_second=2.0)
    start = time.monotonic()
    await limiter.acquire("example.com")
    elapsed = time.monotonic() - start
    assert elapsed < 0.1  # Should be near-instant


async def test_rate_limiter_throttles_sequential_requests() -> None:
    limiter = RateLimiter(rate_per_second=10.0)  # 10 req/s = 100ms between requests

    times = []
    for _ in range(3):
        await limiter.acquire("example.com")
        times.append(time.monotonic())

    # Gap between 1st and 3rd request should be >= ~200ms (2 intervals at 100ms)
    total_time = times[-1] - times[0]
    assert total_time >= 0.15  # Allow some slack


async def test_rate_limiter_independent_per_domain() -> None:
    limiter = RateLimiter(rate_per_second=5.0)  # 200ms between requests

    # First requests to different domains should all be fast
    start = time.monotonic()
    await limiter.acquire("example.com")
    await limiter.acquire("other.com")
    await limiter.acquire("third.com")
    elapsed = time.monotonic() - start

    # Three different domains — should all be near-instant
    assert elapsed < 0.2


async def test_rate_limiter_respects_max_concurrent() -> None:
    limiter = RateLimiter(rate_per_second=100.0, max_concurrent=2)

    active = 0
    max_active = 0

    async def task(domain: str):
        nonlocal active, max_active
        await limiter.acquire(domain)
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)  # Simulate work
        active -= 1
        limiter.release(domain)

    # Launch 5 tasks for the same domain
    await asyncio.gather(*[task("example.com") for _ in range(5)])

    assert max_active <= 2
