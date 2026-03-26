"""Persistent patchright browser lifecycle manager."""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from patchright.async_api import BrowserContext, Page, async_playwright

logger = logging.getLogger(__name__)

# Stable profile dir so Cloudflare clearance cookies persist across scrape runs
_PROFILE_DIR = Path.home() / ".config" / "price_scraper" / "chrome_profile"

# ---------------------------------------------------------------------------
# Browser discovery
# ---------------------------------------------------------------------------

# Each entry: (macos_bundle_id, linux_desktop_name, channel_name or None, executable_paths_by_platform)
# Only Chromium-based browsers are included — patchright cannot drive Firefox/Safari.
_BROWSER_REGISTRY: list[tuple[str, str, str | None, dict[str, list[str]]]] = [
    (
        "com.google.Chrome",
        "google-chrome.desktop",
        "chrome",
        {
            "darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
            "linux":  ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"],
            "win32":  [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ],
        },
    ),
    (
        "com.microsoft.edgemac",
        "microsoft-edge.desktop",
        "msedge",
        {
            "darwin": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
            "linux":  ["/usr/bin/microsoft-edge", "/usr/bin/microsoft-edge-stable"],
            "win32":  [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ],
        },
    ),
    (
        "com.brave.Browser",
        "brave-browser.desktop",
        None,
        {
            "darwin": ["/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"],
            "linux":  ["/usr/bin/brave-browser", "/usr/bin/brave"],
            "win32":  [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
            ],
        },
    ),
    (
        "com.google.Chrome.beta",
        "google-chrome-beta.desktop",
        "chrome-beta",
        {
            "darwin": ["/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta"],
            "linux":  ["/usr/bin/google-chrome-beta"],
            "win32":  [r"C:\Program Files\Google\Chrome Beta\Application\chrome.exe"],
        },
    ),
    (
        "com.operasoftware.Opera",
        "opera.desktop",
        None,
        {
            "darwin": ["/Applications/Opera.app/Contents/MacOS/Opera"],
            "linux":  ["/usr/bin/opera"],
            "win32":  [r"C:\Users\{user}\AppData\Local\Programs\Opera\opera.exe"],
        },
    ),
    (
        "com.vivaldi.Vivaldi",
        "vivaldi.desktop",
        None,
        {
            "darwin": ["/Applications/Vivaldi.app/Contents/MacOS/Vivaldi"],
            "linux":  ["/usr/bin/vivaldi", "/usr/bin/vivaldi-stable"],
            "win32":  [r"C:\Users\{user}\AppData\Local\Vivaldi\Application\vivaldi.exe"],
        },
    ),
    (
        "org.chromium.Chromium",
        "chromium.desktop",
        None,
        {
            "darwin": ["/Applications/Chromium.app/Contents/MacOS/Chromium"],
            "linux":  ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium"],
            "win32":  [r"C:\Program Files\Chromium\Application\chrome.exe"],
        },
    ),
    (
        "company.thebrowser.Browser",
        "",  # Arc is macOS/Windows only
        None,
        {
            "darwin": ["/Applications/Arc.app/Contents/MacOS/Arc"],
            "linux":  [],
            "win32":  [r"C:\Users\{user}\AppData\Local\Programs\Arc\Arc.exe"],
        },
    ),
    (
        "com.google.Chrome.canary",
        "google-chrome-canary.desktop",
        "chrome-canary",
        {
            "darwin": ["/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"],
            "linux":  [],
            "win32":  [r"C:\Users\{user}\AppData\Local\Google\Chrome SxS\Application\chrome.exe"],
        },
    ),
    (
        "com.google.Chrome.dev",
        "google-chrome-unstable.desktop",
        "chrome-dev",
        {
            "darwin": ["/Applications/Google Chrome Dev.app/Contents/MacOS/Google Chrome Dev"],
            "linux":  ["/usr/bin/google-chrome-unstable"],
            "win32":  [],
        },
    ),
]


def _get_frontmost_app() -> str | None:
    """Return the name of the currently focused app (macOS only)."""
    if sys.platform != "darwin":
        return None
    try:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                "tell application \"System Events\" to get name of first application process whose frontmost is true",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as exc:
        logger.debug("Could not get frontmost app: %s", exc)
    return None


def _activate_app(app_name: str) -> None:
    """Bring the named app back to the foreground (macOS only)."""
    if sys.platform != "darwin" or not app_name:
        return
    try:
        subprocess.run(
            ["osascript", "-e", f'tell application "{app_name}" to activate'],
            capture_output=True,
            timeout=2,
        )
    except Exception as exc:
        logger.debug("Could not activate app %r: %s", app_name, exc)


def _detect_default_browser_bundle() -> str | None:
    """Return the default browser's bundle ID (macOS) or .desktop name (Linux)."""
    platform = sys.platform
    try:
        if platform == "darwin":
            result = subprocess.run(
                [
                    "defaults",
                    "read",
                    str(
                        Path.home()
                        / "Library/Preferences/com.apple.LaunchServices/com.apple.launchservices.secure"
                    ),
                    "LSHandlers",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                # Find the https handler entry
                for i, line in enumerate(lines):
                    if "LSHandlerURLScheme" in line and "https" in line:
                        # The role handler bundle ID is usually 2 lines above/below
                        for j in range(max(0, i - 4), min(len(lines), i + 4)):
                            if "LSHandlerRoleAll" in lines[j] and "=" in lines[j]:
                                bundle = lines[j].split("=")[-1].strip().rstrip(";").strip('"')
                                return bundle
        elif platform.startswith("linux"):
            result = subprocess.run(
                ["xdg-settings", "get", "default-web-browser"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        elif platform == "win32":
            import winreg  # type: ignore[import]
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice",
            ) as key:
                prog_id, _ = winreg.QueryValueEx(key, "ProgId")
                return str(prog_id)
    except Exception as exc:
        logger.debug("Default browser detection failed: %s", exc)
    return None


def _find_browser_kwargs() -> dict:
    """
    Return keyword arguments for launch_persistent_context that point to an
    available Chromium-based browser.

    Resolution order:
    1. System default browser (if it's Chromium-based and installed)
    2. Priority-ordered fallback list of the 10 most popular Chromium browsers
    """
    platform = sys.platform
    default_id = _detect_default_browser_bundle()
    logger.debug("Detected default browser identifier: %s", default_id)

    def _entry_matches_default(entry: tuple) -> bool:
        if not default_id:
            return False
        bundle_id, desktop_name, *_ = entry
        id_lower = default_id.lower()
        return (
            bundle_id.lower() in id_lower
            or (desktop_name and desktop_name.lower() in id_lower)
        )

    def _kwargs_for_entry(entry: tuple) -> dict | None:
        _, _, channel, paths_by_platform = entry
        # Prefer a named channel when available (patchright handles path lookup)
        if channel:
            # Verify the channel's binary actually exists before committing to it
            paths = paths_by_platform.get(platform, [])
            if paths and Path(paths[0]).exists():
                return {"channel": channel}
            # On Linux, also check PATH
            if platform.startswith("linux"):
                executable = channel.replace("-", "_")
                if shutil.which(channel) or shutil.which(executable):
                    return {"channel": channel}
            # macOS / Windows: trust that patchright can find the channel
            if platform == "darwin" or platform == "win32":
                if paths and Path(paths[0]).exists():
                    return {"channel": channel}
        # No named channel — find the executable directly
        paths = paths_by_platform.get(platform, [])
        for path_str in paths:
            # Expand {user} placeholder used in some Windows paths
            path_str = path_str.replace("{user}", Path.home().name)
            p = Path(path_str)
            if p.exists():
                return {"executable_path": str(p)}
        # On Linux, also check if the binary is on PATH
        if platform.startswith("linux"):
            for path_str in paths:
                name = Path(path_str).name
                if shutil.which(name):
                    return {"executable_path": shutil.which(name)}
        return None

    # 1. Try to honour the system default first
    for entry in _BROWSER_REGISTRY:
        if _entry_matches_default(entry):
            kwargs = _kwargs_for_entry(entry)
            if kwargs is not None:
                logger.info(
                    "Using system default browser: %s → %s",
                    entry[0],
                    kwargs,
                )
                return kwargs

    # 2. Fall back through the priority list
    for entry in _BROWSER_REGISTRY:
        kwargs = _kwargs_for_entry(entry)
        if kwargs is not None:
            logger.info(
                "Default browser not available; falling back to: %s → %s",
                entry[0],
                kwargs,
            )
            return kwargs

    # 3. Last resort: let patchright try its bundled Chromium
    logger.warning(
        "No supported Chromium-based browser found. "
        "Falling back to patchright's bundled Chromium (stealth may be reduced)."
    )
    return {}


# ---------------------------------------------------------------------------
# Browser manager
# ---------------------------------------------------------------------------


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
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        browser_kwargs = _find_browser_kwargs()
        prev_app = _get_frontmost_app()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(_PROFILE_DIR),
            headless=False,  # patchright requires headless=False for full Cloudflare stealth
            no_viewport=True,
            # Open the window far off-screen so it's invisible even if it
            # briefly reaches the top of the z-order before focus is restored.
            args=["--window-position=-32000,-32000"],
            **browser_kwargs,
        )
        # Chrome steals focus asynchronously after the context is ready, so
        # wait briefly to let that settle before restoring the previous app.
        if prev_app:
            await asyncio.sleep(0.3)
            _activate_app(prev_app)

    async def new_page(self) -> Page:
        """Create a new page, relaunching context if it has been closed."""
        prev_app = _get_frontmost_app()
        if self._context is None:
            await self._launch_context()
        try:
            page = await self._context.new_page()
        except Exception:
            await self._launch_context()
            page = await self._context.new_page()
        await self._minimize_window(page)
        # Opening a new tab can unminimize or foreground the browser window;
        # restore focus to the app that was active before the scrape started.
        if prev_app:
            _activate_app(prev_app)
        return page

    async def _minimize_window(self, page: Page) -> None:
        """Minimize the scraper browser window so it doesn't steal focus."""
        try:
            cdp = await self._context.new_cdp_session(page)
            window_info = await cdp.send("Browser.getWindowForTarget")
            await cdp.send(
                "Browser.setWindowBounds",
                {
                    "windowId": window_info["windowId"],
                    "bounds": {"windowState": "minimized"},
                },
            )
            await cdp.detach()
        except Exception as exc:
            logger.debug("Could not minimize scraper window: %s", exc)

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
