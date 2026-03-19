"""Tests for all 5 retailer extractors using mock Page objects."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from app.scrapers.base import FailureType, ScrapeData, ScrapeError
from app.scrapers.amazon import AmazonExtractor
from app.scrapers.bestbuy import BestBuyExtractor
from app.scrapers.walmart import WalmartExtractor
from app.scrapers.newegg import NeweggExtractor
from app.scrapers.microcenter import MicrocenterExtractor


# --- Helpers ---


def _make_mock_page(
    json_ld: list[dict] | None = None,
    selectors: dict[str, str] | None = None,
    url: str = "https://example.com/product",
    content: str = "<html></html>",
):
    """Build a mock patchright Page.

    Args:
        json_ld: List of JSON-LD objects to embed as script elements.
        selectors: Mapping of CSS selector -> inner_text value.
        url: The page URL.
        content: The full HTML content (for blocked detection).
    """
    page = AsyncMock()
    type(page).url = PropertyMock(return_value=url)
    page.content = AsyncMock(return_value=content)

    # Build script element mocks for JSON-LD
    script_elements = []
    if json_ld:
        for obj in json_ld:
            el = AsyncMock()
            el.inner_text = AsyncMock(return_value=json.dumps(obj))
            script_elements.append(el)

    page.query_selector_all = AsyncMock(
        side_effect=lambda sel: script_elements
        if sel == 'script[type="application/ld+json"]'
        else []
    )

    # CSS selector mocks
    _selectors = selectors or {}

    async def _query_selector(sel):
        if sel in _selectors:
            el = AsyncMock()
            el.inner_text = AsyncMock(return_value=_selectors[sel])
            el.get_attribute = AsyncMock(return_value=_selectors.get(f"{sel}@attr"))
            return el
        return None

    page.query_selector = AsyncMock(side_effect=_query_selector)

    return page


# --- Retailer names ---


def test_amazon_retailer_name():
    assert AmazonExtractor().retailer_name == "Amazon"


def test_bestbuy_retailer_name():
    assert BestBuyExtractor().retailer_name == "Best Buy"


def test_walmart_retailer_name():
    assert WalmartExtractor().retailer_name == "Walmart"


def test_newegg_retailer_name():
    assert NeweggExtractor().retailer_name == "Newegg"


def test_microcenter_retailer_name():
    assert MicrocenterExtractor().retailer_name == "Micro Center"


# --- Domain patterns ---


def test_amazon_domain_patterns():
    assert "amazon.com" in AmazonExtractor().domain_patterns
    assert "www.amazon.com" in AmazonExtractor().domain_patterns


def test_bestbuy_domain_patterns():
    assert "bestbuy.com" in BestBuyExtractor().domain_patterns


def test_walmart_domain_patterns():
    assert "walmart.com" in WalmartExtractor().domain_patterns


def test_newegg_domain_patterns():
    assert "newegg.com" in NeweggExtractor().domain_patterns


def test_microcenter_domain_patterns():
    assert "microcenter.com" in MicrocenterExtractor().domain_patterns


# --- Registration ---


def test_extractors_registered():
    from app.scrapers.registry import get_extractor

    # Ensure all 5 are available
    assert get_extractor("https://www.amazon.com/dp/B0").retailer_name == "Amazon"
    assert get_extractor("https://www.bestbuy.com/site/x").retailer_name == "Best Buy"
    assert get_extractor("https://www.walmart.com/ip/x").retailer_name == "Walmart"
    assert get_extractor("https://www.newegg.com/x").retailer_name == "Newegg"
    assert (
        get_extractor("https://www.microcenter.com/product/1").retailer_name
        == "Micro Center"
    )


# --- Amazon ---


async def test_amazon_extract_json_ld():
    page = _make_mock_page(
        json_ld=[
            {
                "@type": "Product",
                "name": "Sony WH-1000XM5",
                "offers": {"price": "279.99"},
            }
        ],
        url="https://www.amazon.com/dp/B0EXAMPLE",
    )
    ext = AmazonExtractor()
    result = await ext.extract(page, "https://www.amazon.com/dp/B0EXAMPLE")
    assert result.product_name == "Sony WH-1000XM5"
    assert result.price_cents == 27999
    assert result.retailer_name == "Amazon"


async def test_amazon_extract_css_fallback():
    page = _make_mock_page(
        selectors={
            "#productTitle": "Headphones",
            ".a-price-whole": "279",
            ".a-price-fraction": "99",
        },
        url="https://www.amazon.com/dp/B0EXAMPLE",
    )
    ext = AmazonExtractor()
    result = await ext.extract(page, "https://www.amazon.com/dp/B0EXAMPLE")
    assert result.product_name == "Headphones"
    assert result.price_cents == 27999
    assert result.retailer_name == "Amazon"


async def test_amazon_extraction_error():
    page = _make_mock_page(url="https://www.amazon.com/dp/B0EXAMPLE")
    ext = AmazonExtractor()
    with pytest.raises(ScrapeError) as exc_info:
        await ext.extract(page, "https://www.amazon.com/dp/B0EXAMPLE")
    assert exc_info.value.failure_type == FailureType.EXTRACTION_ERROR


# --- Best Buy ---


async def test_bestbuy_extract_json_ld():
    page = _make_mock_page(
        json_ld=[
            {
                "@type": "Product",
                "name": "Samsung Galaxy S24",
                "offers": {"price": "799.99"},
            }
        ],
        url="https://www.bestbuy.com/site/samsung",
    )
    ext = BestBuyExtractor()
    result = await ext.extract(page, "https://www.bestbuy.com/site/samsung")
    assert result.product_name == "Samsung Galaxy S24"
    assert result.price_cents == 79999
    assert result.retailer_name == "Best Buy"


async def test_bestbuy_extract_css_fallback():
    page = _make_mock_page(
        selectors={
            ".sku-title h1": "LG Monitor",
            ".priceView-customer-price span": "$349.99",
        },
        url="https://www.bestbuy.com/site/lg",
    )
    ext = BestBuyExtractor()
    result = await ext.extract(page, "https://www.bestbuy.com/site/lg")
    assert result.product_name == "LG Monitor"
    assert result.price_cents == 34999
    assert result.retailer_name == "Best Buy"


# --- Walmart ---


async def test_walmart_extract_next_data():
    next_data = {
        "props": {
            "pageProps": {
                "initialData": {
                    "data": {
                        "product": {
                            "name": "iPad Air",
                            "priceInfo": {"currentPrice": {"price": 449.00}},
                        }
                    }
                }
            }
        }
    }
    page = AsyncMock()
    type(page).url = PropertyMock(return_value="https://www.walmart.com/ip/ipad")
    page.content = AsyncMock(return_value="<html></html>")
    page.query_selector_all = AsyncMock(return_value=[])

    # Mock __NEXT_DATA__ script element
    next_data_el = AsyncMock()
    next_data_el.inner_text = AsyncMock(return_value=json.dumps(next_data))

    async def _qs(sel):
        if sel == "#__NEXT_DATA__":
            return next_data_el
        return None

    page.query_selector = AsyncMock(side_effect=_qs)

    ext = WalmartExtractor()
    result = await ext.extract(page, "https://www.walmart.com/ip/ipad")
    assert result.product_name == "iPad Air"
    assert result.price_cents == 44900
    assert result.retailer_name == "Walmart"


async def test_walmart_extract_json_ld_fallback():
    page = _make_mock_page(
        json_ld=[
            {
                "@type": "Product",
                "name": "Roku Stick",
                "offers": {"price": "29.99"},
            }
        ],
        url="https://www.walmart.com/ip/roku",
    )
    # Override query_selector to return None for __NEXT_DATA__
    original_qs = page.query_selector.side_effect

    async def _qs(sel):
        if sel == "#__NEXT_DATA__":
            return None
        return await original_qs(sel)

    page.query_selector = AsyncMock(side_effect=_qs)

    ext = WalmartExtractor()
    result = await ext.extract(page, "https://www.walmart.com/ip/roku")
    assert result.product_name == "Roku Stick"
    assert result.price_cents == 2999


# --- Newegg ---


async def test_newegg_extract_json_ld():
    page = _make_mock_page(
        json_ld=[
            {
                "@type": "Product",
                "name": "EVGA RTX 3080",
                "offers": {"price": "699.99"},
            }
        ],
        url="https://www.newegg.com/evga",
    )
    ext = NeweggExtractor()
    result = await ext.extract(page, "https://www.newegg.com/evga")
    assert result.product_name == "EVGA RTX 3080"
    assert result.price_cents == 69999
    assert result.retailer_name == "Newegg"


async def test_newegg_extract_css_fallback():
    page = _make_mock_page(
        selectors={
            ".product-title": "Corsair RAM 32GB",
            ".price-current": "$89.99",
        },
        url="https://www.newegg.com/corsair",
    )
    ext = NeweggExtractor()
    result = await ext.extract(page, "https://www.newegg.com/corsair")
    assert result.product_name == "Corsair RAM 32GB"
    assert result.price_cents == 8999


# --- Micro Center ---


async def test_microcenter_extract_json_ld():
    page = _make_mock_page(
        json_ld=[
            {
                "@type": "Product",
                "name": "AMD Ryzen 9 7950X",
                "offers": {"price": "549.99"},
            }
        ],
        url="https://www.microcenter.com/product/123",
    )
    ext = MicrocenterExtractor()
    result = await ext.extract(page, "https://www.microcenter.com/product/123")
    assert result.product_name == "AMD Ryzen 9 7950X"
    assert result.price_cents == 54999
    assert result.retailer_name == "Micro Center"


async def test_microcenter_extract_css_fallback():
    page = _make_mock_page(
        selectors={
            "#pricing span": "$399.99",
            "h1.product-title": "Intel i9-14900K",
        },
        url="https://www.microcenter.com/product/456",
    )
    ext = MicrocenterExtractor()
    result = await ext.extract(page, "https://www.microcenter.com/product/456")
    assert result.product_name == "Intel i9-14900K"
    assert result.price_cents == 39999
