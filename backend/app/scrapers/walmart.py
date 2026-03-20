"""Walmart product page extractor."""

from __future__ import annotations

import json
import re

from patchright.async_api import Page

from app.scrapers.base import BaseExtractor, FailureType, ScrapeData, ScrapeError
from app.scrapers.registry import register_extractor

# Bot-wall signals checked against the page TITLE only (not the full HTML body,
# which contains JS bundles that trigger false positives on normal product pages).
# Walmart challenge pages have distinctive titles; product pages never do.
_BLOCK_TITLE_SIGNALS = (
    "robot",
    "captcha",
    "human verification",
    "please verify",
    "just a moment",
    "access denied",
    "are you a human",
)


def _find_price_in_product(product: dict) -> float | None:
    """Walk known priceInfo paths; return first numeric price found."""
    price_info = product.get("priceInfo", {})
    for key in ("currentPrice", "wasPrice", "priceRange"):
        node = price_info.get(key)
        if isinstance(node, dict):
            p = node.get("price") or node.get("minPrice", {}).get("price")
            if p is not None:
                return float(p)
        # priceRange sometimes wraps min/max dicts
        if isinstance(node, dict) and "minPrice" in node:
            p = node["minPrice"].get("price")
            if p is not None:
                return float(p)
    # last-resort: regex scan the priceInfo JSON string
    raw = json.dumps(price_info)
    m = re.search(r'"price"\s*:\s*(\d+(?:\.\d+)?)', raw)
    if m:
        return float(m.group(1))
    return None


class WalmartExtractor(BaseExtractor):
    """Extracts product data from Walmart product pages."""

    @property
    def retailer_name(self) -> str:
        return "Walmart"

    @property
    def domain_patterns(self) -> list[str]:
        return ["walmart.com", "www.walmart.com"]

    async def extract(self, page: Page, url: str) -> ScrapeData:
        # Wait for full page load so __NEXT_DATA__ is populated
        try:
            await page.wait_for_load_state("load", timeout=20000)
        except Exception:
            pass  # proceed and attempt extraction anyway

        # Bot-wall detection: check title and URL, not the full HTML body.
        # JS bundles in the full body contain strings like "captcha" / "_pxid"
        # on every normal Walmart page, causing false-positive BLOCKED errors.
        raw_title = await page.title()
        current_url = page.url.lower()
        if any(sig in raw_title.lower() for sig in _BLOCK_TITLE_SIGNALS) or "px.walmart.com" in current_url:
            raise ScrapeError(FailureType.BLOCKED, f"Bot detection on Walmart page (title: {raw_title!r})")

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
                price = _find_price_in_product(product)
                if name and price is not None:
                    return ScrapeData(
                        product_name=name,
                        price_cents=int(round(price * 100)),
                        listing_url=str(page.url),
                        retailer_name=self.retailer_name,
                    )
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                pass

        # Try JSON-LD fallback
        result = await self._try_json_ld(page)
        if result:
            return result

        # CSS fallback — current Walmart selectors (2024-2025)
        name_el = await page.query_selector(
            'h1[itemprop="name"], h1[data-automation="product-title"], [data-testid="product-title"]'
        )
        price_el = (
            await page.query_selector('[itemprop="price"]')
            or await page.query_selector('[data-testid="price-wrap"]')
            or await page.query_selector('[data-automation="buybox-price"]')
            or await page.query_selector('span.price-characteristic')
            or await page.query_selector('[data-testid="price-container"]')
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
