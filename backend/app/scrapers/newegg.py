"""Newegg product page extractor."""

from __future__ import annotations

from patchright.async_api import Page

from app.scrapers.base import BaseExtractor, FailureType, ScrapeData, ScrapeError
from app.scrapers.registry import register_extractor


class NeweggExtractor(BaseExtractor):
    """Extracts product data from Newegg product pages."""

    @property
    def retailer_name(self) -> str:
        return "Newegg"

    @property
    def domain_patterns(self) -> list[str]:
        return ["newegg.com", "www.newegg.com"]

    async def extract(self, page: Page, url: str) -> ScrapeData:
        # Check for bot detection
        content = await page.content()
        if "captcha" in content.lower() or "are you a human" in content.lower():
            raise ScrapeError(FailureType.BLOCKED, "Bot detection on Newegg page")

        # Try JSON-LD first (Newegg typically has good JSON-LD)
        result = await self._try_json_ld(page)
        if result:
            return result

        # CSS fallback
        name_el = await page.query_selector(".product-title")
        price_el = await page.query_selector(".price-current")

        if name_el and price_el:
            name = (await name_el.inner_text()).strip()
            price_text = (await price_el.inner_text()).strip()
            return ScrapeData(
                product_name=name,
                price_cents=self._parse_price_to_cents(price_text),
                listing_url=str(page.url),
                retailer_name=self.retailer_name,
            )

        raise ScrapeError(
            FailureType.EXTRACTION_ERROR,
            "Could not extract product data from Newegg page",
        )


register_extractor(NeweggExtractor())
