"""Amazon product page extractor."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from patchright.async_api import Page

from app.scrapers.base import BaseExtractor, FailureType, ScrapeData, ScrapeError
from app.scrapers.registry import register_extractor

_ASIN_RE = re.compile(r"/dp/([A-Z0-9]{10})")


def _clean_amazon_url(url: str) -> str:
    """Return a clean /dp/{ASIN} URL, stripping tracking params (dib, crid, etc.)
    that cause Amazon to serve comparison-shopping pages with third-party offers."""
    parsed = urlparse(url)
    m = _ASIN_RE.search(parsed.path)
    if m:
        return f"https://www.amazon.com/dp/{m.group(1)}"
    return url  # non-ASIN URL, leave as-is


class AmazonExtractor(BaseExtractor):
    """Extracts product data from Amazon product pages."""

    @property
    def retailer_name(self) -> str:
        return "Amazon"

    @property
    def domain_patterns(self) -> list[str]:
        return ["amazon.com", "www.amazon.com"]

    async def extract(self, page: Page, url: str) -> ScrapeData:
        # If the current URL still has tracking params, navigate to the clean ASIN URL
        clean = _clean_amazon_url(url)
        if clean != url:
            await page.goto(clean, wait_until="domcontentloaded", timeout=30000)
        # Check for bot detection
        content = await page.content()
        if "captcha" in content.lower():
            raise ScrapeError(FailureType.BLOCKED, "CAPTCHA detected on Amazon page")

        # Try JSON-LD first (most reliable)
        result = await self._try_json_ld(page)
        if result:
            return result

        # CSS fallback
        name_el = await page.query_selector("#productTitle")
        whole_el = await page.query_selector(".a-price-whole")
        fraction_el = await page.query_selector(".a-price-fraction")

        if name_el and whole_el and fraction_el:
            name = (await name_el.inner_text()).strip()
            whole = (await whole_el.inner_text()).strip().rstrip(".")
            fraction = (await fraction_el.inner_text()).strip()
            price_str = f"${whole}.{fraction}"
            return ScrapeData(
                product_name=name,
                price_cents=self._parse_price_to_cents(price_str),
                listing_url=str(page.url),
                retailer_name=self.retailer_name,
            )

        raise ScrapeError(
            FailureType.EXTRACTION_ERROR,
            "Could not extract product data from Amazon page",
        )


register_extractor(AmazonExtractor())
