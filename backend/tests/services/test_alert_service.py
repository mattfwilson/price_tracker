"""Tests for the alert evaluation service."""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from app.models.alert import Alert
from app.models.retailer_url import RetailerUrl
from app.models.scrape_job import ScrapeJob
from app.models.scrape_result import ScrapeResult
from app.models.watch_query import WatchQuery
from app.services.alert_service import evaluate_alerts_for_job, should_fire_alert


@pytest_asyncio.fixture
async def watch_query(db_session):
    wq = WatchQuery(name="Alert Test Query", threshold_cents=1000, is_active=True, schedule="daily")
    db_session.add(wq)
    await db_session.flush()
    return wq


@pytest_asyncio.fixture
async def retailer_url(db_session, watch_query):
    ru = RetailerUrl(watch_query_id=watch_query.id, url="https://example.com/product")
    db_session.add(ru)
    await db_session.flush()
    return ru


@pytest_asyncio.fixture
async def scrape_job(db_session, watch_query):
    job = ScrapeJob(
        watch_query_id=watch_query.id,
        status="success",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db_session.add(job)
    await db_session.flush()
    return job


async def _create_result(session, retailer_url_id, scrape_job_id, price_cents, created_at=None):
    """Helper to create a ScrapeResult."""
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


class TestShouldFireAlert:
    @pytest.mark.asyncio
    async def test_below_threshold_first_time(self, db_session, retailer_url, scrape_job):
        """price 800 <= threshold 1000, no previous result -> True."""
        await _create_result(db_session, retailer_url.id, scrape_job.id, 800)
        result = await should_fire_alert(db_session, retailer_url.id, 800, 1000)
        assert result is True

    @pytest.mark.asyncio
    async def test_at_threshold(self, db_session, retailer_url, scrape_job):
        """price 1000 <= threshold 1000 -> True (first breach)."""
        await _create_result(db_session, retailer_url.id, scrape_job.id, 1000)
        result = await should_fire_alert(db_session, retailer_url.id, 1000, 1000)
        assert result is True

    @pytest.mark.asyncio
    async def test_above_threshold(self, db_session, retailer_url, scrape_job):
        """price 1200 > threshold 1000 -> False."""
        await _create_result(db_session, retailer_url.id, scrape_job.id, 1200)
        result = await should_fire_alert(db_session, retailer_url.id, 1200, 1000)
        assert result is False

    @pytest.mark.asyncio
    async def test_continued_breach(self, db_session, retailer_url, scrape_job):
        """current 800 <= 1000, previous 900 (also <= 1000) -> False (continued breach)."""
        now = datetime.utcnow()
        await _create_result(db_session, retailer_url.id, scrape_job.id, 900, created_at=now - timedelta(hours=1))
        await _create_result(db_session, retailer_url.id, scrape_job.id, 800, created_at=now)
        result = await should_fire_alert(db_session, retailer_url.id, 800, 1000)
        assert result is False

    @pytest.mark.asyncio
    async def test_rebreach(self, db_session, retailer_url, scrape_job):
        """previous 1200 (above), current 800 (below) -> True (re-breach)."""
        now = datetime.utcnow()
        await _create_result(db_session, retailer_url.id, scrape_job.id, 1200, created_at=now - timedelta(hours=1))
        await _create_result(db_session, retailer_url.id, scrape_job.id, 800, created_at=now)
        result = await should_fire_alert(db_session, retailer_url.id, 800, 1000)
        assert result is True


class TestEvaluateAlertsForJob:
    @pytest.mark.asyncio
    async def test_creates_records_for_breaches(self, db_session, watch_query, retailer_url, scrape_job):
        """Job with 2 results below threshold (both first breach) -> 2 Alert records."""
        # Create a second retailer URL
        ru2 = RetailerUrl(watch_query_id=watch_query.id, url="https://example.com/product2")
        db_session.add(ru2)
        await db_session.flush()

        # Create results below threshold for both
        await _create_result(db_session, retailer_url.id, scrape_job.id, 800)
        await _create_result(db_session, ru2.id, scrape_job.id, 900)

        alerts = await evaluate_alerts_for_job(db_session, watch_query.id, scrape_job.id)
        assert len(alerts) == 2
        assert all(isinstance(a, Alert) for a in alerts)

    @pytest.mark.asyncio
    async def test_skips_above_threshold(self, db_session, watch_query, retailer_url, scrape_job):
        """Job with result at 1500 (threshold 1000) -> 0 alerts."""
        await _create_result(db_session, retailer_url.id, scrape_job.id, 1500)

        alerts = await evaluate_alerts_for_job(db_session, watch_query.id, scrape_job.id)
        assert len(alerts) == 0
