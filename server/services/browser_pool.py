"""Browser pool manager for Playwright browsers."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import Browser, async_playwright
from server.config import MAX_BROWSERS
from server.utils.logging_config import get_logger

logger = get_logger(__name__)


class BrowserPool:
    """Manages a pool of Playwright browsers for concurrent scraping (Singleton)."""

    _instance: "BrowserPool | None" = None
    _initialized: bool = False
    _lock_class = asyncio.Lock()

    def __new__(cls):
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize browser pool."""
        # Only initialize once
        if self._initialized:
            return

        self.max_browsers = MAX_BROWSERS
        self._semaphore = asyncio.Semaphore(MAX_BROWSERS)
        self._playwright = None
        self._browsers: list[Browser] = []
        self._lock = asyncio.Lock()
        self._ref_count = 0
        self._initialized = True

    async def __aenter__(self):
        """Start the browser pool (reference counted)."""
        async with self._lock:
            self._ref_count += 1
            if self._ref_count == 1:
                # First reference, start playwright
                logger.info("Starting browser pool")
                self._playwright = await async_playwright().start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close all browsers and cleanup (reference counted)."""
        async with self._lock:
            self._ref_count -= 1
            if self._ref_count == 0:
                # Last reference, cleanup
                logger.info("Shutting down browser pool")
                for browser in self._browsers:
                    try:
                        await browser.close()
                    except Exception as e:
                        logger.error("Error closing browser", error=str(e))
                self._browsers.clear()

                if self._playwright:
                    await self._playwright.stop()
                    self._playwright = None

    @asynccontextmanager
    async def get_browser(self) -> AsyncIterator[Browser]:
        """Get a browser from the pool.

        Yields:
            A Playwright browser instance
        """
        async with self._semaphore:
            # Acquire or create a browser
            browser = await self._acquire_browser()
            try:
                yield browser
            finally:
                # Browser is kept alive for reuse, no need to close
                pass

    async def _acquire_browser(self) -> Browser:
        """Acquire a browser from the pool or create a new one.

        Returns:
            A Playwright browser instance
        """
        async with self._lock:
            # Reuse an existing browser if available
            if self._browsers:
                return self._browsers[0]

            # Create a new browser
            if not self._playwright:
                raise RuntimeError(
                    f"BrowserPool not initialized. Use async with. "
                    f"ref_count={self._ref_count}, playwright={self._playwright}, "
                    f"browsers={len(self._browsers)}"
                )

            browser = await self._playwright.chromium.launch(headless=True)
            self._browsers.append(browser)
            logger.debug("Created new browser", total_browsers=len(self._browsers))
            return browser


# Global singleton instance
_browser_pool_instance: BrowserPool | None = None


def get_browser_pool() -> BrowserPool:
    """Get the global browser pool singleton instance.

    Returns:
        The global BrowserPool instance
    """
    global _browser_pool_instance
    if _browser_pool_instance is None:
        _browser_pool_instance = BrowserPool()
    return _browser_pool_instance
