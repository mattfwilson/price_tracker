"""Micro Center product page extractor.

Extraction strategy (in priority order):
1. JSON-LD / schema.org structured data — most stable
2. Microdata itemprop attributes — standard across site redesigns
3. CSS selectors — legacy fallback

Bot detection: Micro Center uses light/standard CDN-level protection (not enterprise
bot management). The persistent patchright browser profile is more than sufficient.
"""

from __future__ import annotations

import logging
import random

from patchright.async_api import Page

from app.scrapers.base import BaseExtractor, FailureType, ScrapeData, ScrapeError
from app.scrapers.registry import register_extractor

logger = logging.getLogger(__name__)

_BLOCK_TITLES = ("access denied", "403 forbidden", "blocked", "captcha")


class MicrocenterExtractor(BaseExtractor):
    """Extracts product data from Micro Center product pages."""

    @property
    def retailer_name(self) -> str:
        return "Micro Center"

    @property
    def domain_patterns(self) -> list[str]:
        return ["microcenter.com", "www.microcenter.com"]

    async def extract(self, page: Page, url: str) -> ScrapeData:
        # Wait for price element — covers SSR pages and any light JS rendering
        try:
            await page.wait_for_selector(
                "[itemprop='price'], #pricing span, .price > span, span.price",
                timeout=12000,
            )
        except Exception:
            pass

        # Small human-like delay
        await page.wait_for_timeout(random.randint(800, 2000))

        # Block detection via title and URL (avoids false positives from page body text)
        title = (await page.title()).lower()
        current_url = page.url.lower()
        if any(s in title for s in _BLOCK_TITLES):
            raise ScrapeError(
                FailureType.BLOCKED,
                f"Bot detection on Micro Center page (title: {title!r})",
            )
        if "captcha" in current_url or current_url.endswith("/error"):
            raise ScrapeError(
                FailureType.BLOCKED,
                "Redirected to error/captcha on Micro Center",
            )

        # Strategy 1: JSON-LD
        result = await self._try_json_ld(page)
        if result:
            return result

        # Strategy 2: schema.org microdata (itemprop attributes — stable across redesigns)
        name_el = (
            await page.query_selector("[itemprop='name']")
            or await page.query_selector("h1.product-title")
            or await page.query_selector("h1")
        )
        price_el = (
            await page.query_selector("[itemprop='price']")
            or await page.query_selector("#pricing span")
            or await page.query_selector("span.price")
            or await page.query_selector(".price > span")
        )

        if name_el and price_el:
            name = (await name_el.inner_text()).strip()
            # itemprop="price" often carries the numeric value in a content attribute
            price_content = await price_el.get_attribute("content")
            price_text = price_content or (await price_el.inner_text()).strip()
            return ScrapeData(
                product_name=name,
                price_cents=self._parse_price_to_cents(price_text),
                listing_url=str(page.url),
                retailer_name=self.retailer_name,
            )

        raise ScrapeError(
            FailureType.EXTRACTION_ERROR,
            "Could not extract product data from Micro Center page",
        )


register_extractor(MicrocenterExtractor())
