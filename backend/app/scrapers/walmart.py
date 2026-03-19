"""Walmart product page extractor."""

from __future__ import annotations

import json

from patchright.async_api import Page

from app.scrapers.base import BaseExtractor, FailureType, ScrapeData, ScrapeError
from app.scrapers.registry import register_extractor


class WalmartExtractor(BaseExtractor):
    """Extracts product data from Walmart product pages."""

    @property
    def retailer_name(self) -> str:
        return "Walmart"

    @property
    def domain_patterns(self) -> list[str]:
        return ["walmart.com", "www.walmart.com"]

    async def extract(self, page: Page, url: str) -> ScrapeData:
        # Check for bot detection
        content = await page.content()
        if "captcha" in content.lower() or "robot" in content.lower():
            raise ScrapeError(FailureType.BLOCKED, "Bot detection on Walmart page")

        # Try __NEXT_DATA__ first (Walmart-specific)
        next_data_el = await page.query_selector("#__NEXT_DATA__")
        if next_data_el:
            try:
                text = await next_data_el.inner_text()
                data = json.loads(text)
                product = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("initialData", {})
                    .get("data", {})
                    .get("product", {})
                )
                name = product.get("name")
                price_info = product.get("priceInfo", {})
                current_price = price_info.get("currentPrice", {})
                price = current_price.get("price")
                if name and price is not None:
                    return ScrapeData(
                        product_name=name,
                        price_cents=int(round(float(price) * 100)),
                        listing_url=str(page.url),
                        retailer_name=self.retailer_name,
                    )
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                pass

        # Try JSON-LD fallback
        result = await self._try_json_ld(page)
        if result:
            return result

        # CSS fallback
        name_el = await page.query_selector('[itemprop="name"]')
        price_el = (
            await page.query_selector('[itemprop="price"]')
            or await page.query_selector('span[data-testid="price-wrap"]')
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
            "Could not extract product data from Walmart page",
        )


register_extractor(WalmartExtractor())
