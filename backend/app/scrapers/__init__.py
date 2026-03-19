"""Scraping infrastructure: extractors, registry, and browser management."""

from app.scrapers.base import BaseExtractor, FailureType, ScrapeData, ScrapeError
from app.scrapers.browser import BrowserManager
from app.scrapers.registry import get_extractor, register_extractor

# Import extractor modules to trigger registration
from app.scrapers import amazon  # noqa: F401
from app.scrapers import bestbuy  # noqa: F401
from app.scrapers import walmart  # noqa: F401
from app.scrapers import newegg  # noqa: F401
from app.scrapers import microcenter  # noqa: F401

__all__ = [
    "BaseExtractor",
    "BrowserManager",
    "FailureType",
    "ScrapeData",
    "ScrapeError",
    "get_extractor",
    "register_extractor",
]
