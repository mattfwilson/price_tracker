"""Tests for price delta calculation."""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from app.models.retailer_url import RetailerUrl
from app.models.scrape_job import ScrapeJob
from app.models.scrape_result import ScrapeResult
from app.models.watch_query import WatchQuery
from app.services.scrape_service import calculate_price_delta


@pytest_asyncio.fixture
async def watch_query(db_session):
    """Create a WatchQuery for test use."""
    wq = WatchQuery(name="Test Query", threshold_cents=5000, is_active=True, schedule="daily")
    db_session.add(wq)
    await db_session.flush()
    return wq


@pytest_asyncio.fixture
async def retailer_url(db_session, watch_query):
    """Create a RetailerUrl for test use."""
    ru = RetailerUrl(watch_query_id=watch_query.id, url="https://example.com/product")
    db_session.add(ru)
    await db_session.flush()
    return ru


@pytest_asyncio.fixture
async def scrape_job(db_session, watch_query):
    """Create a ScrapeJob for test use."""
    job = ScrapeJob(
        watch_query_id=watch_query.id,
        status="success",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db_session.add(job)
    await db_session.flush()
    return job


async def _create_scrape_result(session, retailer_url_id, scrape_job_id, price_cents, created_at=None):
    """Helper to create a ScrapeResult with a specific price."""
    result = ScrapeResult(
        retailer_url_id=retailer_url_id,
        scrape_job_id=scrape_job_id,
        product_name="Test Product",
        price_cents=price_cents,
        listing_url="https://example.com/product",
        retailer_name="Example",
    )
    if created_at is not None:
        result.created_at = created_at
    session.add(result)
    await session.flush()
    return result


@pytest.mark.asyncio
async def test_first_scrape_delta(db_session, retailer_url):
    """No previous result -> returns 'new' direction with zero delta."""
    result = await calculate_price_delta(db_session, retailer_url.id, 10000)
    assert result == {"direction": "new", "delta_cents": 0, "pct_change": 0.0}


@pytest.mark.asyncio
async def test_price_higher(db_session, retailer_url, scrape_job):
    """Current price higher than previous -> 'higher' with positive delta."""
    await _create_scrape_result(db_session, retailer_url.id, scrape_job.id, 10000)
    result = await calculate_price_delta(db_session, retailer_url.id, 12000)
    assert result == {"direction": "higher", "delta_cents": 2000, "pct_change": 20.0}


@pytest.mark.asyncio
async def test_price_lower(db_session, retailer_url, scrape_job):
    """Current price lower than previous -> 'lower' with negative delta."""
    await _create_scrape_result(db_session, retailer_url.id, scrape_job.id, 10000)
    result = await calculate_price_delta(db_session, retailer_url.id, 8000)
    assert result == {"direction": "lower", "delta_cents": -2000, "pct_change": -20.0}


@pytest.mark.asyncio
async def test_price_unchanged(db_session, retailer_url, scrape_job):
    """Same price -> 'unchanged' with zero delta."""
    await _create_scrape_result(db_session, retailer_url.id, scrape_job.id, 10000)
    result = await calculate_price_delta(db_session, retailer_url.id, 10000)
    assert result == {"direction": "unchanged", "delta_cents": 0, "pct_change": 0.0}


@pytest.mark.asyncio
async def test_pct_change_rounding(db_session, retailer_url, scrape_job):
    """Percentage change rounds to 2 decimal places."""
    await _create_scrape_result(db_session, retailer_url.id, scrape_job.id, 3333)
    result = await calculate_price_delta(db_session, retailer_url.id, 3334)
    assert result["pct_change"] == 0.03
    assert result["direction"] == "higher"
    assert result["delta_cents"] == 1


@pytest.mark.asyncio
async def test_zero_previous_price(db_session, retailer_url, scrape_job):
    """Previous price of 0 -> pct_change=0.0, avoids division by zero."""
    await _create_scrape_result(db_session, retailer_url.id, scrape_job.id, 0)
    result = await calculate_price_delta(db_session, retailer_url.id, 1000)
    assert result == {"direction": "higher", "delta_cents": 1000, "pct_change": 0.0}


@pytest.mark.asyncio
async def test_uses_most_recent_result(db_session, retailer_url, scrape_job):
    """Delta is calculated against the most recent previous result."""
    now = datetime.utcnow()
    # Older result at 5000 cents
    await _create_scrape_result(
        db_session, retailer_url.id, scrape_job.id, 5000,
        created_at=now - timedelta(hours=2),
    )
    # Newer result at 8000 cents
    await _create_scrape_result(
        db_session, retailer_url.id, scrape_job.id, 8000,
        created_at=now - timedelta(hours=1),
    )
    # Current is 10000 -> delta should be vs 8000 (most recent), not 5000
    result = await calculate_price_delta(db_session, retailer_url.id, 10000)
    assert result == {"direction": "higher", "delta_cents": 2000, "pct_change": 25.0}
