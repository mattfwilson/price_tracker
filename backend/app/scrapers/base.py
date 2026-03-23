"""Base contracts for scraping infrastructure."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import httpx
from patchright.async_api import Page

# Realistic browser headers for HTTP-only scrapers
_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

_JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


class FailureType(str, Enum):
    NETWORK_ERROR = "NETWORK_ERROR"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    BLOCKED = "BLOCKED"


@dataclass
class ScrapeData:
    """Matches ScrapeResult model fields exactly."""

    product_name: str
    price_cents: int
    listing_url: str
    retailer_name: str


class ScrapeError(Exception):
    """Raised by extractors with failure classification."""

    def __init__(self, failure_type: FailureType, message: str):
        self.failure_type = failure_type
        self.message = message
        super().__init__(f"{failure_type.value}: {message}")


class BaseExtractor(ABC):
    """Abstract base for site-specific extractors."""

    @property
    @abstractmethod
    def retailer_name(self) -> str:
        """Human-readable retailer name (e.g., 'Amazon')."""
        ...

    @property
    @abstractmethod
    def domain_patterns(self) -> list[str]:
        """URL domain patterns this extractor handles."""
        ...

    @property
    def supports_http_scrape(self) -> bool:
        """Return True if this extractor can scrape without a browser."""
        return False

    async def http_scrape(self, url: str) -> ScrapeData:
        """Scrape without a browser. Only called when supports_http_scrape is True."""
        raise NotImplementedError

    async def pre_navigate(self, page: Page, url: str) -> None:
        """Optional hook called before page.goto(url). Override for site-specific warm-up."""

    @abstractmethod
    async def extract(self, page: Page, url: str) -> ScrapeData:
        """Extract product data from page. Raise ScrapeError on failure."""
        ...

    async def _http_get(self, url: str) -> str:
        """Fetch raw HTML via httpx with browser-like headers. Raises ScrapeError on failure."""
        try:
            async with httpx.AsyncClient(
                headers=_HTTP_HEADERS,
                follow_redirects=True,
                timeout=20,
            ) as client:
                resp = await client.get(url)
        except Exception as exc:
            raise ScrapeError(FailureType.NETWORK_ERROR, str(exc))
        if resp.status_code in (403, 429, 503):
            raise ScrapeError(FailureType.BLOCKED, f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            raise ScrapeError(FailureType.NETWORK_ERROR, f"HTTP {resp.status_code}")
        return resp.text

    def _parse_json_ld_from_html(self, html: str, listing_url: str) -> ScrapeData | None:
        """Extract product data from JSON-LD embedded in raw HTML."""
        for m in _JSON_LD_RE.finditer(html):
            try:
                data = json.loads(m.group(1))
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") == "Product":
                        offers = item.get("offers", {})
                        if isinstance(offers, list):
                            offers = offers[0]
                        price = offers.get("price")
                        name = item.get("name")
                        if price and name:
                            return ScrapeData(
                                product_name=name,
                                price_cents=int(round(float(price) * 100)),
                                listing_url=listing_url,
                                retailer_name=self.retailer_name,
                            )
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        return None

    def _parse_price_to_cents(self, price_str: str) -> int:
        """Common price parsing: '$1,299.99' -> 129999"""
        cleaned = "".join(price_str.split()).replace("$", "").replace(",", "")
        return int(round(float(cleaned) * 100))

    async def _try_json_ld(self, page: Page) -> ScrapeData | None:
        """Try extracting from JSON-LD structured data (most reliable)."""
        scripts = await page.query_selector_all('script[type="application/ld+json"]')
        for script in scripts:
            text = await script.inner_text()
            try:
                data = json.loads(text)
                # Handle both single object and array
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") == "Product":
                        offers = item.get("offers", {})
                        if isinstance(offers, list):
                            offers = offers[0]
                        price = offers.get("price")
                        name = item.get("name")
                        if price and name:
                            return ScrapeData(
                                product_name=name,
                                price_cents=int(round(float(price) * 100)),
                                listing_url=str(page.url),
                                retailer_name=self.retailer_name,
                            )
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        return None
