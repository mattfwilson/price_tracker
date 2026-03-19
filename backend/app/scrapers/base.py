"""Base contracts for scraping infrastructure."""

from __future__ import annotations

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

    @abstractmethod
    async def extract(self, page: Page, url: str) -> ScrapeData:
        """Extract product data from page. Raise ScrapeError on failure."""
        ...

    def _parse_price_to_cents(self, price_str: str) -> int:
        """Common price parsing: '$1,299.99' -> 129999"""
        cleaned = price_str.replace("$", "").replace(",", "").strip()
        return int(round(float(cleaned) * 100))
