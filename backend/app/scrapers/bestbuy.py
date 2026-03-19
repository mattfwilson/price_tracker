"""Best Buy product page extractor."""

from __future__ import annotations

from patchright.async_api import Page

from app.scrapers.base import BaseExtractor, ScrapeData, ScrapeError, FailureType
from app.scrapers.registry import register_extractor


class BestBuyExtractor(BaseExtractor):
    """Extracts product data from Best Buy product pages."""

    @property
    def retailer_name(self) -> str:
        return "Best Buy"

    @property
    def domain_patterns(self) -> list[str]:
        return ["bestbuy.com", "www.bestbuy.com"]

    async def extract(self, page: Page, url: str) -> ScrapeData:
        raise NotImplementedError("Full extraction in Task 2")


register_extractor(BestBuyExtractor())
