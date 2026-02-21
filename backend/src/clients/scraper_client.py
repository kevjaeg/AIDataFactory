from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from loguru import logger


@dataclass
class ScrapeResult:
    """Result from scraping a single URL."""
    url: str
    html: str | None
    status_code: int | None
    method: str  # "httpx" or "playwright"
    error: str | None = None
    title: str | None = None
    language: str | None = None


class ScraperClient:
    """Scrapes URLs using httpx with optional Playwright fallback."""

    USER_AGENT = "AIDataFactory/0.1.0 (+https://github.com/ai-data-factory)"
    TIMEOUT = 30.0  # seconds

    def __init__(self) -> None:
        self._robots_cache: dict[str, RobotFileParser] = {}

    async def scrape_url(
        self,
        url: str,
        use_playwright: str = "auto",
        retry_attempts: int = 3,
    ) -> ScrapeResult:
        """Scrape a URL. Tries httpx first, falls back to Playwright if needed.

        Args:
            url: The URL to scrape.
            use_playwright: "auto" (fallback), "always", or "never".
            retry_attempts: Number of retry attempts for transient failures.
        """
        if use_playwright == "always":
            return await self._scrape_with_playwright(url)

        # Try httpx first
        result = await self._scrape_with_httpx(url, retry_attempts)

        if use_playwright == "auto" and self._needs_playwright(result):
            logger.info(f"httpx result looks JS-rendered, falling back to Playwright: {url}")
            return await self._scrape_with_playwright(url)

        return result

    async def _scrape_with_httpx(self, url: str, retry_attempts: int = 3) -> ScrapeResult:
        """Scrape using httpx (fast path for static pages)."""
        last_error = None
        for attempt in range(retry_attempts):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=self.TIMEOUT,
                    headers={"User-Agent": self.USER_AGENT},
                ) as client:
                    response = await client.get(url)

                    if response.status_code == 200:
                        html = response.text

                        # Extract basic metadata from headers
                        language = None
                        if "content-language" in response.headers:
                            language = response.headers["content-language"].split(",")[0].strip()

                        return ScrapeResult(
                            url=url,
                            html=html,
                            status_code=response.status_code,
                            method="httpx",
                            language=language,
                        )
                    else:
                        last_error = f"HTTP {response.status_code}"

            except Exception as e:
                last_error = str(e)
                if attempt < retry_attempts - 1:
                    import asyncio
                    wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                    logger.warning(f"Retry {attempt + 1}/{retry_attempts} for {url}: {e}")
                    await asyncio.sleep(wait)

        return ScrapeResult(
            url=url,
            html=None,
            status_code=None,
            method="httpx",
            error=last_error,
        )

    async def _scrape_with_playwright(self, url: str) -> ScrapeResult:
        """Scrape using Playwright (for JS-heavy pages)."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return ScrapeResult(
                url=url,
                html=None,
                status_code=None,
                method="playwright",
                error="Playwright not installed. Install with: pip install playwright && playwright install chromium",
            )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=self.USER_AGENT)

                response = await page.goto(url, wait_until="networkidle", timeout=self.TIMEOUT * 1000)
                html = await page.content()
                status_code = response.status if response else None
                title = await page.title()

                await browser.close()

                return ScrapeResult(
                    url=url,
                    html=html,
                    status_code=status_code,
                    method="playwright",
                    title=title,
                )
        except Exception as e:
            return ScrapeResult(
                url=url,
                html=None,
                status_code=None,
                method="playwright",
                error=str(e),
            )

    def _needs_playwright(self, result: ScrapeResult) -> bool:
        """Heuristic: does the httpx result look like it needs JS rendering?"""
        if result.error or result.html is None:
            return True
        html = result.html.strip().lower()
        # Very short body often means JS-rendered content
        if len(html) < 500:
            return True
        # Common JS framework indicators in otherwise empty pages
        js_indicators = [
            'id="__next"',      # Next.js
            'id="app"',         # Vue.js
            'id="root"',        # React
            "<noscript>",         # Noscript fallback = JS required
        ]
        body_content = html.split("<body")[1] if "<body" in html else html
        # If body is mostly empty except for a single div + scripts
        if body_content.count("<p") == 0 and body_content.count("<article") == 0:
            for indicator in js_indicators:
                if indicator in body_content:
                    return True
        return False

    async def check_robots_txt(self, url: str) -> bool:
        """Check if we're allowed to scrape this URL per robots.txt."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        if robots_url in self._robots_cache:
            rp = self._robots_cache[robots_url]
            return rp.can_fetch(self.USER_AGENT, url)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url)
                rp = RobotFileParser()
                rp.parse(response.text.splitlines())
                self._robots_cache[robots_url] = rp
                return rp.can_fetch(self.USER_AGENT, url)
        except Exception:
            # If we can't fetch robots.txt, assume allowed
            logger.debug(f"Could not fetch robots.txt for {parsed.netloc}, allowing scrape")
            return True
