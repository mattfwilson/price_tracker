"""Persistent patchright browser lifecycle manager."""

from __future__ import annotations

from pathlib import Path

from patchright.async_api import BrowserContext, Page, async_playwright

# Stable profile dir so Cloudflare clearance cookies persist across scrape runs
_PROFILE_DIR = Path.home() / ".config" / "price_scraper" / "chrome_profile"


class BrowserManager:
    """Manages a persistent patchright browser context."""

    def __init__(self) -> None:
        self._playwright = None
        self._context: BrowserContext | None = None

    async def start(self) -> None:
        """Start playwright and launch browser context."""
        self._playwright = await async_playwright().start()
        await self._launch_context()

    async def _launch_context(self) -> None:
        """Launch a persistent browser context with stealth settings."""
        _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(_PROFILE_DIR),
            channel="chrome",
            headless=False,  # patchright requires headless=False for full Cloudflare stealth
            no_viewport=True,
        )

    async def new_page(self) -> Page:
        """Create a new page, relaunching context if it has been closed."""
        if self._context is None:
            await self._launch_context()
        try:
            return await self._context.new_page()
        except Exception:
            await self._launch_context()
            return await self._context.new_page()

    async def close_browser(self) -> None:
        """Close the Chrome window without stopping playwright.
        Next call to new_page() will relaunch the context fresh."""
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        self._context = None

    async def restart(self) -> None:
        """Restart browser context on error."""
        await self.close_browser()
        await self._launch_context()

    async def stop(self) -> None:
        """Close browser context and stop playwright."""
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
