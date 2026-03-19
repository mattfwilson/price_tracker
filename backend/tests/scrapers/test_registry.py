"""Tests for base contracts (ScrapeData, FailureType, ScrapeError) and registry."""

import pytest

from app.scrapers.base import BaseExtractor, FailureType, ScrapeData, ScrapeError
from app.scrapers.registry import get_extractor


# --- ScrapeData ---


def test_scrape_data_fields():
    data = ScrapeData(
        product_name="X",
        price_cents=999,
        listing_url="http://example.com",
        retailer_name="Amazon",
    )
    assert data.product_name == "X"
    assert data.price_cents == 999
    assert data.listing_url == "http://example.com"
    assert data.retailer_name == "Amazon"


# --- FailureType ---


def test_failure_type_values():
    assert FailureType.NETWORK_ERROR == "NETWORK_ERROR"
    assert FailureType.EXTRACTION_ERROR == "EXTRACTION_ERROR"
    assert FailureType.BLOCKED == "BLOCKED"


# --- ScrapeError ---


def test_scrape_error_message_format():
    err = ScrapeError(FailureType.NETWORK_ERROR, "timeout")
    assert str(err) == "NETWORK_ERROR: timeout"
    assert err.failure_type == FailureType.NETWORK_ERROR
    assert err.message == "timeout"


# --- Price parsing ---


def test_parse_price_to_cents():
    """Create a concrete subclass just to test the shared helper."""
    from unittest.mock import AsyncMock

    class _Stub(BaseExtractor):
        @property
        def retailer_name(self) -> str:
            return "Test"

        @property
        def domain_patterns(self) -> list[str]:
            return ["test.com"]

        async def extract(self, page, url):
            ...

    stub = _Stub()
    assert stub._parse_price_to_cents("$1,299.99") == 129999


def test_parse_price_to_cents_no_comma():
    from unittest.mock import AsyncMock

    class _Stub(BaseExtractor):
        @property
        def retailer_name(self) -> str:
            return "Test"

        @property
        def domain_patterns(self) -> list[str]:
            return ["test.com"]

        async def extract(self, page, url):
            ...

    stub = _Stub()
    assert stub._parse_price_to_cents("$29.99") == 2999


def test_parse_price_to_cents_whole_dollar():
    class _Stub(BaseExtractor):
        @property
        def retailer_name(self) -> str:
            return "Test"

        @property
        def domain_patterns(self) -> list[str]:
            return ["test.com"]

        async def extract(self, page, url):
            ...

    stub = _Stub()
    assert stub._parse_price_to_cents("$100") == 10000


# --- Registry ---


def test_get_extractor_amazon():
    ext = get_extractor("https://www.amazon.com/dp/B0EXAMPLE")
    assert ext.retailer_name == "Amazon"


def test_get_extractor_bestbuy():
    ext = get_extractor("https://www.bestbuy.com/site/something")
    assert ext.retailer_name == "Best Buy"


def test_get_extractor_walmart():
    ext = get_extractor("https://www.walmart.com/ip/something")
    assert ext.retailer_name == "Walmart"


def test_get_extractor_newegg():
    ext = get_extractor("https://www.newegg.com/something")
    assert ext.retailer_name == "Newegg"


def test_get_extractor_microcenter():
    ext = get_extractor("https://www.microcenter.com/product/123")
    assert ext.retailer_name == "Micro Center"


def test_get_extractor_unknown_domain():
    with pytest.raises(ValueError):
        get_extractor("https://unknown.com/something")


def test_get_extractor_without_www():
    ext = get_extractor("https://amazon.com/dp/B0EXAMPLE")
    assert ext.retailer_name == "Amazon"
