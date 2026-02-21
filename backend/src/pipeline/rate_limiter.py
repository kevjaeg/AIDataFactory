import asyncio
import time
from collections import defaultdict

from loguru import logger


class RateLimiter:
    """Per-domain async rate limiter with concurrency control.

    Uses token bucket algorithm for rate limiting and semaphores for concurrency.
    """

    def __init__(
        self,
        rate_per_second: float = 2.0,
        max_concurrent: int = 3,
    ) -> None:
        self._rate_per_second = rate_per_second
        self._interval = 1.0 / rate_per_second
        self._max_concurrent = max_concurrent
        self._last_request: dict[str, float] = defaultdict(float)
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._lock = asyncio.Lock()

    def _get_semaphore(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._semaphores:
            self._semaphores[domain] = asyncio.Semaphore(self._max_concurrent)
        return self._semaphores[domain]

    async def acquire(self, domain: str) -> None:
        """Wait until we're allowed to make a request to this domain."""
        sem = self._get_semaphore(domain)
        await sem.acquire()

        async with self._lock:
            now = time.monotonic()
            last = self._last_request[domain]
            wait_time = self._interval - (now - last)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request[domain] = time.monotonic()

    def release(self, domain: str) -> None:
        """Release the concurrency semaphore for this domain."""
        if domain in self._semaphores:
            self._semaphores[domain].release()
