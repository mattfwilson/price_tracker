"""Best Buy product page extractor."""

from __future__ import annotations

from patchright.async_api import Page

from app.scrapers.base import BaseExtractor, FailureType, ScrapeData, ScrapeError
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
        # Check for bot detection
        content = await page.content()
        if "captcha" in content.lower() or "blocked" in content.lower():
            raise ScrapeError(FailureType.BLOCKED, "Bot detection on Best Buy page")

        # Try JSON-LD first
        result = await self._try_json_ld(page)
        if result:
            return result

        # CSS fallback
        name_el = (
            await page.query_selector(".sku-title h1")
            or await page.query_selector('[data-testid="heading"]')
        )
        price_el = (
            await page.query_selector('[data-testid="customer-price"] span')
            or await page.query_selector(".priceView-customer-price span")
        )

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
            "Could not extract product data from Best Buy page",
        )


register_extractor(BestBuyExtractor())
