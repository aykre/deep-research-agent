"""Web scraping service using Playwright or BeautifulSoup."""

import httpx
from bs4 import BeautifulSoup

from server.services.browser_pool import BrowserPool, get_browser_pool


async def scrape_page_with_beautifulsoup(url: str, timeout: int = 10) -> str:
    """Scrape a web page using BeautifulSoup and httpx.

    Args:
        url: The URL to scrape
        timeout: Timeout in seconds

    Returns:
        The text content of the page (limited to 10000 chars)
    """
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        response = await client.get(url, headers=headers)
        response.raise_for_status()

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text content
        content = soup.get_text(separator=" ", strip=True)

        return content[:10000]  # Limit to 10k chars


async def scrape_page_with_playwright(
    url: str, browser_pool: BrowserPool, timeout: int = 10000
) -> str:
    """Scrape a web page using Playwright headless browser from a pool.

    Args:
        url: The URL to scrape
        browser_pool: Browser pool to get browser from
        timeout: Timeout in milliseconds

    Returns:
        The text content of the page (limited to 10000 chars)
    """
    async with browser_pool.get_browser() as browser:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

            # Get text content
            content = await page.inner_text("body")

            return content[:10000]  # Limit to 10k chars
        finally:
            await context.close()


async def scrape_page(
    url: str,
    timeout: int = 10000,
    use_playwright: bool = False,
    browser_pool: BrowserPool | None = None,
) -> str:
    """Scrape a web page using BeautifulSoup or Playwright.

    Args:
        url: The URL to scrape
        timeout: Timeout (milliseconds for Playwright, seconds for BeautifulSoup)
        use_playwright: If True, use Playwright; otherwise use BeautifulSoup
        browser_pool: Browser pool for Playwright mode (required if use_playwright=True)

    Returns:
        The text content of the page (limited to 10000 chars)
    """
    if use_playwright:
        browser_pool = get_browser_pool()

        if browser_pool is None:
            raise ValueError("browser_pool is required when use_playwright=True")
        return await scrape_page_with_playwright(url, browser_pool, timeout)
    else:
        # Convert milliseconds to seconds for httpx
        timeout_seconds = int(timeout / 1000)
        return await scrape_page_with_beautifulsoup(url, timeout_seconds)
