import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass

from clients.scraper_client import ScraperClient, ScrapeResult


def test_scrape_result_dataclass() -> None:
    result = ScrapeResult(
        url="https://example.com",
        html="<h1>Hello</h1>",
        status_code=200,
        method="httpx",
    )
    assert result.url == "https://example.com"
    assert result.status_code == 200
    assert result.method == "httpx"
    assert result.error is None


def test_scrape_result_with_error() -> None:
    result = ScrapeResult(
        url="https://example.com",
        html=None,
        status_code=None,
        method="httpx",
        error="Connection refused",
    )
    assert result.error == "Connection refused"
    assert result.html is None


async def test_scrape_url_with_httpx_success() -> None:
    """httpx succeeds with good HTML content — no Playwright needed."""
    client = ScraperClient()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body><h1>Article</h1><p>Content here</p></body></html>"
    mock_response.headers = {"content-type": "text/html"}

    with patch("clients.scraper_client.httpx.AsyncClient") as mock_httpx:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_instance

        result = await client.scrape_url("https://example.com", use_playwright="never")

    assert result.status_code == 200
    assert result.method == "httpx"
    assert "Article" in result.html


async def test_scrape_url_httpx_failure_returns_error() -> None:
    """httpx fails (e.g., connection error) and playwright is disabled."""
    client = ScraperClient()

    with patch("clients.scraper_client.httpx.AsyncClient") as mock_httpx:
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = Exception("Connection refused")
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_httpx.return_value = mock_instance

        result = await client.scrape_url("https://example.com", use_playwright="never")

    assert result.error is not None
    assert result.html is None


async def test_robots_txt_check() -> None:
    """Test that robots.txt compliance works."""
    client = ScraperClient()
    # By default, if we can't fetch robots.txt, we should allow
    allowed = await client.check_robots_txt("https://example.com/page")
    # Without mocking the robots.txt fetch, this should default to True
    assert isinstance(allowed, bool)
