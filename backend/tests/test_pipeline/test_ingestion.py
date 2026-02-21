import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile

from pipeline.stages.ingestion import SpiderStage
from pipeline.base import StageResult
from clients.scraper_client import ScrapeResult


async def test_spider_stage_name() -> None:
    stage = SpiderStage(data_dir=Path(tempfile.mkdtemp()))
    assert stage.stage_name == "spider"


async def test_spider_validate_input_valid() -> None:
    stage = SpiderStage(data_dir=Path(tempfile.mkdtemp()))
    assert await stage.validate_input(["https://example.com"]) is True


async def test_spider_validate_input_empty() -> None:
    stage = SpiderStage(data_dir=Path(tempfile.mkdtemp()))
    assert await stage.validate_input([]) is False


async def test_spider_validate_input_invalid_urls() -> None:
    stage = SpiderStage(data_dir=Path(tempfile.mkdtemp()))
    assert await stage.validate_input(["not-a-url"]) is False


async def test_spider_process_success() -> None:
    """Spider successfully scrapes URLs and saves HTML files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        stage = SpiderStage(data_dir=Path(tmpdir))

        mock_result = ScrapeResult(
            url="https://example.com/article",
            html="<html><body><h1>Test Article</h1><p>Content</p></body></html>",
            status_code=200,
            method="httpx",
        )

        with patch.object(stage, '_scraper') as mock_scraper:
            mock_scraper.scrape_url = AsyncMock(return_value=mock_result)
            mock_scraper.check_robots_txt = AsyncMock(return_value=True)

            result = await stage.process(
                input_data=["https://example.com/article"],
                config={
                    "job_id": 1,
                    "scraping": {
                        "max_concurrent": 3,
                        "use_playwright": "never",
                        "respect_robots_txt": True,
                        "rate_limit": 2.0,
                    }
                },
            )

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["url"] == "https://example.com/article"
        assert result.data[0]["status_code"] == 200
        assert result.stats["total_urls"] == 1
        assert result.stats["successful"] == 1


async def test_spider_process_with_robots_blocked() -> None:
    """Spider respects robots.txt and skips blocked URLs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        stage = SpiderStage(data_dir=Path(tmpdir))

        with patch.object(stage, '_scraper') as mock_scraper:
            mock_scraper.check_robots_txt = AsyncMock(return_value=False)

            result = await stage.process(
                input_data=["https://example.com/blocked"],
                config={
                    "job_id": 1,
                    "scraping": {
                        "max_concurrent": 3,
                        "use_playwright": "never",
                        "respect_robots_txt": True,
                        "rate_limit": 2.0,
                    }
                },
            )

        assert result.success is True
        assert len(result.data) == 0
        assert result.stats["robots_blocked"] == 1


async def test_spider_process_scrape_failure() -> None:
    """Spider handles scrape failures gracefully (partial results)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        stage = SpiderStage(data_dir=Path(tmpdir))

        mock_result = ScrapeResult(
            url="https://example.com/fail",
            html=None,
            status_code=None,
            method="httpx",
            error="Connection refused",
        )

        with patch.object(stage, '_scraper') as mock_scraper:
            mock_scraper.scrape_url = AsyncMock(return_value=mock_result)
            mock_scraper.check_robots_txt = AsyncMock(return_value=True)

            result = await stage.process(
                input_data=["https://example.com/fail"],
                config={
                    "job_id": 1,
                    "scraping": {
                        "max_concurrent": 3,
                        "use_playwright": "never",
                        "respect_robots_txt": True,
                        "rate_limit": 2.0,
                    }
                },
            )

        assert result.success is True  # Partial success is still success
        assert len(result.data) == 0
        assert result.stats["failed"] == 1
        assert len(result.errors) == 1
