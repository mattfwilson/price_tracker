"""Persistent patchright browser lifecycle manager."""

from __future__ import annotations

from patchright.async_api import BrowserContext, Page, async_playwright


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
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir="/tmp/patchright_profile",
            channel="chrome",
            headless=True,
            no_viewport=True,
        )

    async def new_page(self) -> Page:
        """Create a new page, launching context if needed."""
        if self._context is None:
            await self._launch_context()
        return await self._context.new_page()

    async def restart(self) -> None:
        """Restart browser context on error."""
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        self._context = None
        await self._launch_context()

    async def stop(self) -> None:
        """Close browser context and stop playwright."""
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
