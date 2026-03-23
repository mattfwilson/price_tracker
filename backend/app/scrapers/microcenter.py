"""Micro Center product page extractor.

Extraction strategy (in priority order):
1. HTTP-only (no browser) — JSON-LD from raw HTML; fast and invisible
2. JSON-LD / schema.org structured data via browser — most stable
3. Microdata itemprop attributes — standard across site redesigns
4. CSS selectors — legacy fallback

Bot detection: Micro Center uses light/standard CDN-level protection (not enterprise
bot management), so plain HTTP requests succeed reliably.
"""

from __future__ import annotations

import logging
import random
import re

from patchright.async_api import Page

from app.scrapers.base import BaseExtractor, FailureType, ScrapeData, ScrapeError
from app.scrapers.registry import register_extractor

logger = logging.getLogger(__name__)

_BLOCK_TITLES = ("access denied", "403 forbidden", "blocked", "captcha")

# Matches itemprop="price" with either a content="…" attribute or inner text
_ITEMPROP_PRICE_RE = re.compile(
    r'itemprop=["\']price["\'][^>]*content=["\']([^"\']+)["\']'
    r'|itemprop=["\']price["\'][^>]*>\s*([^<]+?)\s*<',
    re.IGNORECASE,
)
_ITEMPROP_NAME_RE = re.compile(
    r'itemprop=["\']name["\'][^>]*>\s*([^<]+?)\s*<',
    re.IGNORECASE,
)


class MicrocenterExtractor(BaseExtractor):
    """Extracts product data from Micro Center product pages."""

    @property
    def retailer_name(self) -> str:
        return "Micro Center"

    @property
    def domain_patterns(self) -> list[str]:
        return ["microcenter.com", "www.microcenter.com"]

    @property
    def supports_http_scrape(self) -> bool:
        return True

    async def http_scrape(self, url: str) -> ScrapeData:
        """Fetch and parse without a browser — works reliably against Micro Center's light bot protection."""
        html = await self._http_get(url)

        # Block detection via title
        title_m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        title = title_m.group(1).lower() if title_m else ""
        if any(s in title for s in _BLOCK_TITLES):
            raise ScrapeError(FailureType.BLOCKED, f"Bot detection (title: {title!r})")

        # Strategy 1: JSON-LD
        result = self._parse_json_ld_from_html(html, url)
        if result:
            return result

        # Strategy 2: itemprop microdata
        price_m = _ITEMPROP_PRICE_RE.search(html)
        name_m = _ITEMPROP_NAME_RE.search(html)
        if price_m and name_m:
            price_str = (price_m.group(1) or price_m.group(2)).strip()
            name = name_m.group(1).strip()
            return ScrapeData(
                product_name=name,
                price_cents=self._parse_price_to_cents(price_str),
                listing_url=url,
                retailer_name=self.retailer_name,
            )

        raise ScrapeError(FailureType.EXTRACTION_ERROR, "Could not extract product data via HTTP")

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
