"""Base contracts for scraping infrastructure."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from patchright.async_api import Page


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

    async def pre_navigate(self, page: Page, url: str) -> None:
        """Optional hook called before page.goto(url). Override for site-specific warm-up."""

    @abstractmethod
    async def extract(self, page: Page, url: str) -> ScrapeData:
        """Extract product data from page. Raise ScrapeError on failure."""
        ...

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
