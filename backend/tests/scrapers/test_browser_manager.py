"""Tests for BrowserManager initialization (no live browser needed)."""

from app.scrapers.browser import BrowserManager


def test_browser_manager_attributes():
    bm = BrowserManager()
    assert bm._playwright is None
    assert bm._context is None
