"""Tests for retry logic in scrape_single_url."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tenacity import RetryError

from app.scrapers.base import FailureType, ScrapeData, ScrapeError
from app.services.scrape_service import scrape_single_url


def _make_mock_browser() -> MagicMock:
    """Create a mock BrowserManager with async new_page."""
    browser = MagicMock()
    page = AsyncMock()
    page.goto = AsyncMock()
    page.close = AsyncMock()
    browser.new_page = AsyncMock(return_value=page)
    return browser


def _make_scrape_data() -> ScrapeData:
    return ScrapeData(
        product_name="Test",
        price_cents=1999,
        listing_url="https://amazon.com/dp/test",
        retailer_name="Amazon",
    )


@pytest.mark.asyncio
async def test_retries_on_network_error():
    """NETWORK_ERROR triggers retries, called 4 times total (1 + 3 retries)."""
    browser = _make_mock_browser()
    mock_extractor = AsyncMock(
        side_effect=ScrapeError(FailureType.NETWORK_ERROR, "timeout")
    )

    with patch("app.services.scrape_service.get_extractor") as mock_get:
        mock_get.return_value.extract = mock_extractor
        with patch("app.services.scrape_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises((ScrapeError, RetryError)):
                await scrape_single_url(browser, "https://amazon.com/dp/test")

    assert mock_extractor.call_count == 4


@pytest.mark.asyncio
async def test_retries_on_extraction_error():
    """EXTRACTION_ERROR triggers retries, called 4 times total."""
    browser = _make_mock_browser()
    mock_extractor = AsyncMock(
        side_effect=ScrapeError(FailureType.EXTRACTION_ERROR, "no price")
    )

    with patch("app.services.scrape_service.get_extractor") as mock_get:
        mock_get.return_value.extract = mock_extractor
        with patch("app.services.scrape_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises((ScrapeError, RetryError)):
                await scrape_single_url(browser, "https://amazon.com/dp/test")

    assert mock_extractor.call_count == 4


@pytest.mark.asyncio
async def test_no_retry_on_blocked():
    """BLOCKED errors fail immediately with no retry (called exactly once)."""
    browser = _make_mock_browser()
    mock_extractor = AsyncMock(
        side_effect=ScrapeError(FailureType.BLOCKED, "captcha")
    )

    with patch("app.services.scrape_service.get_extractor") as mock_get:
        mock_get.return_value.extract = mock_extractor
        with patch("app.services.scrape_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ScrapeError) as exc_info:
                await scrape_single_url(browser, "https://amazon.com/dp/test")

    assert exc_info.value.failure_type == FailureType.BLOCKED
    assert mock_extractor.call_count == 1


@pytest.mark.asyncio
async def test_success_no_retry():
    """Successful scrape on first call -- called exactly once."""
    browser = _make_mock_browser()
    expected = _make_scrape_data()
    mock_extractor = AsyncMock(return_value=expected)

    with patch("app.services.scrape_service.get_extractor") as mock_get:
        mock_get.return_value.extract = mock_extractor
        with patch("app.services.scrape_service.asyncio.sleep", new_callable=AsyncMock):
            result = await scrape_single_url(browser, "https://amazon.com/dp/test")

    assert result == expected
    assert mock_extractor.call_count == 1


@pytest.mark.asyncio
async def test_success_after_retry():
    """Fails twice then succeeds -- called 3 times, returns data."""
    browser = _make_mock_browser()
    expected = _make_scrape_data()
    mock_extractor = AsyncMock(
        side_effect=[
            ScrapeError(FailureType.NETWORK_ERROR, "fail 1"),
            ScrapeError(FailureType.NETWORK_ERROR, "fail 2"),
            expected,
        ]
    )

    with patch("app.services.scrape_service.get_extractor") as mock_get:
        mock_get.return_value.extract = mock_extractor
        with patch("app.services.scrape_service.asyncio.sleep", new_callable=AsyncMock):
            result = await scrape_single_url(browser, "https://amazon.com/dp/test")

    assert result == expected
    assert mock_extractor.call_count == 3


@pytest.mark.asyncio
async def test_backoff_timing():
    """Verify exponential backoff waits of 2s, 4s, 8s via tenacity sleep mock."""
    browser = _make_mock_browser()
    mock_extractor = AsyncMock(
        side_effect=ScrapeError(FailureType.NETWORK_ERROR, "timeout")
    )
    sleep_calls = []

    async def mock_sleep(seconds):
        sleep_calls.append(seconds)

    with patch("app.services.scrape_service.get_extractor") as mock_get:
        mock_get.return_value.extract = mock_extractor
        with patch("app.services.scrape_service.asyncio.sleep", side_effect=mock_sleep):
            with patch("tenacity.nap.sleep", side_effect=mock_sleep):
                with pytest.raises((ScrapeError, RetryError)):
                    await scrape_single_url(browser, "https://amazon.com/dp/test")

    # Tenacity backoff sleeps are exactly 2.0, 4.0, 8.0
    # Human-delay sleeps are random in [0.5, 2.0) -- filter by checking exact known values
    backoff_sleeps = [s for s in sleep_calls if s in (2.0, 4.0, 8.0)]
    assert len(backoff_sleeps) == 3
    assert backoff_sleeps[0] == 2.0
    assert backoff_sleeps[1] == 4.0
    assert backoff_sleeps[2] == 8.0
