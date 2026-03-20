"""Best Buy product page extractor.

Extraction strategy (in priority order):
1. Best Buy Products API — bypasses all bot detection; requires PRICE_SCRAPER_BESTBUY_API_KEY
2. JSON-LD structured data — most stable browser-based approach
3. CSS selectors — fallback for layout variants

Bot detection: Best Buy uses Akamai Bot Manager (_abck / bm_sz cookies).
Mitigation: persistent Chrome profile (accumulates behavioral trust), homepage
warm-up on cold sessions, mouse movement simulation, and extended post-load delays.
"""

from __future__ import annotations

import logging
import random
import re

import httpx
from patchright.async_api import Page

from app.core.config import settings
from app.scrapers.base import BaseExtractor, FailureType, ScrapeData, ScrapeError
from app.scrapers.registry import register_extractor

logger = logging.getLogger(__name__)

# SKU is the numeric segment before ".p" in Best Buy product URLs
_SKU_RE = re.compile(r"/(\d{5,8})\.p")

# Akamai challenge page title patterns
_AKAMAI_BLOCK_TITLES = (
    "access denied",
    "robot check",
    "security check",
    "just a moment",
    "checking your browser",
    "please wait",
    "captcha",
    "blocked",
)


class BestBuyExtractor(BaseExtractor):
    """Extracts product data from Best Buy product pages."""

    @property
    def retailer_name(self) -> str:
        return "Best Buy"

    @property
    def domain_patterns(self) -> list[str]:
        return ["bestbuy.com", "www.bestbuy.com"]

    async def pre_navigate(self, page: Page, url: str) -> None:
        """Warm up the session with a Best Buy homepage visit if Akamai has not yet
        issued a session cookie (_abck). A warmed profile builds behavioral trust and
        significantly reduces Akamai challenges on the product page."""
        try:
            cookies = await page.context.cookies("https://www.bestbuy.com")
            has_abck = any(c["name"] == "_abck" for c in cookies)
            if not has_abck:
                logger.debug("BestBuy: no _abck cookie — warming up session via homepage")
                await page.goto(
                    "https://www.bestbuy.com",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                # Simulate human reading the page before navigating
                await page.mouse.move(
                    random.randint(400, 800),
                    random.randint(300, 600),
                    steps=random.randint(10, 25),
                )
                await page.wait_for_timeout(random.randint(2500, 4500))
        except Exception as exc:
            # Warm-up failure is non-fatal — proceed to product page
            logger.debug("BestBuy: homepage warm-up failed (%s), continuing", exc)

    async def extract(self, page: Page, url: str) -> ScrapeData:
        # --- Strategy 1: Official Best Buy Products API (no bot detection) ---
        if settings.bestbuy_api_key:
            result = await self._try_api(url)
            if result:
                return result

        # --- Strategy 2 & 3: Browser-based extraction ---
        return await self._extract_from_browser(page, url)

    async def _try_api(self, url: str) -> ScrapeData | None:
        """Call the Best Buy Products API using the SKU extracted from the URL."""
        match = _SKU_RE.search(url)
        if not match:
            logger.debug("BestBuy API: could not extract SKU from URL %s", url)
            return None

        sku = match.group(1)
        api_url = (
            f"https://api.bestbuy.com/v1/products/{sku}.json"
            f"?show=sku,name,salePrice,regularPrice,onSale"
            f"&apiKey={settings.bestbuy_api_key}"
        )
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(api_url)
            if resp.status_code != 200:
                logger.debug("BestBuy API: HTTP %s for SKU %s", resp.status_code, sku)
                return None
            data = resp.json()
            name = data.get("name")
            # Use salePrice when on sale, otherwise regularPrice
            price = data.get("salePrice") or data.get("regularPrice")
            if not name or price is None:
                return None
            return ScrapeData(
                product_name=name,
                price_cents=int(round(float(price) * 100)),
                listing_url=url,
                retailer_name=self.retailer_name,
            )
        except Exception as exc:
            logger.debug("BestBuy API: request failed (%s), falling back to browser", exc)
            return None

    async def _extract_from_browser(self, page: Page, url: str) -> ScrapeData:
        """Browser-based extraction with Akamai mitigation."""
        # Wait for React to hydrate the price element
        try:
            await page.wait_for_selector(
                "[data-testid='customer-price'], .priceView-customer-price",
                timeout=15000,
            )
        except Exception:
            pass  # Check for block below; element may still be present

        # Simulate human interaction while page finishes loading
        await page.mouse.move(
            random.randint(300, 900),
            random.randint(200, 700),
            steps=random.randint(10, 25),
        )
        await page.wait_for_timeout(random.randint(1500, 3000))

        # Check for Akamai / generic bot detection
        title = (await page.title()).lower()
        if any(s in title for s in _AKAMAI_BLOCK_TITLES):
            raise ScrapeError(
                FailureType.BLOCKED,
                f"Bot detection on Best Buy page (title: {title!r})",
            )

        # Validate Akamai session cookie is present (absent = silent block)
        cookies = await page.context.cookies("https://www.bestbuy.com")
        has_abck = any(c["name"] == "_abck" for c in cookies)
        if not has_abck:
            raise ScrapeError(
                FailureType.BLOCKED,
                "Akamai session not established (missing _abck)",
            )

        # JSON-LD (most stable across layout A/B tests)
        result = await self._try_json_ld(page)
        if result:
            return result

        # CSS selectors (confirmed 2024-2025)
        name_el = (
            await page.query_selector("[data-testid='heading']")
            or await page.query_selector("h1.heading-5")
            or await page.query_selector(".sku-title h1")
        )
        # aria-hidden span contains the formatted price string ("$1,299.99")
        price_el = (
            await page.query_selector("[data-testid='customer-price'] span[aria-hidden='true']")
            or await page.query_selector("[data-testid='customer-price'] span")
            or await page.query_selector("[data-testid='price-info-price']")
            or await page.query_selector(".priceView-customer-price span[aria-hidden='true']")
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
