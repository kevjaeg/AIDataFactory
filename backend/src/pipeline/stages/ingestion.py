import asyncio
import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from pipeline.base import PipelineStage, StageResult
from pipeline.rate_limiter import RateLimiter
from clients.scraper_client import ScraperClient


class SpiderStage(PipelineStage):
    """Stage 1: Scrape URLs and save raw HTML."""

    stage_name = "spider"

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._scraper = ScraperClient()

    async def validate_input(self, input_data: Any) -> bool:
        """Validate that input is a non-empty list of valid URLs."""
        if not isinstance(input_data, list) or len(input_data) == 0:
            return False
        for url in input_data:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
        return True

    async def process(self, input_data: list[str], config: dict) -> StageResult:
        """Scrape all URLs and return raw documents."""
        scraping_config = config.get("scraping", {})
        job_id = config.get("job_id", 0)

        rate_limit = scraping_config.get("rate_limit", 2.0)
        max_concurrent = scraping_config.get("max_concurrent", 3)
        use_playwright = scraping_config.get("use_playwright", "auto")
        respect_robots = scraping_config.get("respect_robots_txt", True)

        limiter = RateLimiter(rate_per_second=rate_limit, max_concurrent=max_concurrent)

        # Create output directory for raw HTML
        raw_dir = self._data_dir / "raw" / str(job_id)
        raw_dir.mkdir(parents=True, exist_ok=True)

        results: list[dict] = []
        errors: list[str] = []
        stats = {
            "total_urls": len(input_data),
            "successful": 0,
            "failed": 0,
            "robots_blocked": 0,
        }

        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_one(url: str) -> None:
            async with semaphore:
                domain = urlparse(url).netloc

                # Check robots.txt
                if respect_robots:
                    allowed = await self._scraper.check_robots_txt(url)
                    if not allowed:
                        logger.info(f"Blocked by robots.txt: {url}")
                        stats["robots_blocked"] += 1
                        return

                # Rate limit
                await limiter.acquire(domain)
                try:
                    result = await self._scraper.scrape_url(
                        url, use_playwright=use_playwright
                    )
                finally:
                    limiter.release(domain)

                if result.error or result.html is None:
                    stats["failed"] += 1
                    errors.append(f"Failed to scrape {url}: {result.error}")
                    logger.warning(f"Failed to scrape {url}: {result.error}")
                    return

                # Save HTML to file
                url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
                html_path = raw_dir / f"{url_hash}.html"
                html_path.write_text(result.html, encoding="utf-8")

                doc = {
                    "url": url,
                    "html_path": str(html_path),
                    "status_code": result.status_code,
                    "method": result.method,
                    "title": result.title,
                    "language": result.language,
                }
                results.append(doc)
                stats["successful"] += 1
                logger.info(f"Scraped {url} ({result.method}, {result.status_code})")

        # Scrape all URLs concurrently
        tasks = [scrape_one(url) for url in input_data]
        await asyncio.gather(*tasks, return_exceptions=True)

        return StageResult(
            success=True,  # Partial success counts
            data=results,
            errors=errors,
            stats=stats,
        )
