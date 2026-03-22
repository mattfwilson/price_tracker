"""Tests for ScrapeResult and ScrapeJob repository operations."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scrape_job import ScrapeJob
from app.models.scrape_result import ScrapeResult
from app.models.watch_query import WatchQuery
from app.models.retailer_url import RetailerUrl
from app.repositories.scrape_result import (
    create_scrape_job,
    create_scrape_result,
    get_latest_scrape_result,
    get_rolling_avg_price,
    get_all_time_min_price,
    update_scrape_job,
)
from app.repositories.alert import is_within_cooldown
from app.models.alert import Alert


async def _create_prerequisites(db: AsyncSession) -> tuple[int, int]:
    """Create a WatchQuery and RetailerUrl, return (watch_query_id, retailer_url_id)."""
    wq = WatchQuery(name="Test", threshold_cents=1999)
    db.add(wq)
    await db.flush()
    ru = RetailerUrl(watch_query_id=wq.id, url="https://amazon.com/dp/test")
    db.add(ru)
    await db.flush()
    return wq.id, ru.id


async def test_create_scrape_job(db_session: AsyncSession):
    """Creates ScrapeJob with status='running' and started_at set."""
    wq_id, _ = await _create_prerequisites(db_session)

    job = await create_scrape_job(db_session, wq_id)

    assert job.id is not None
    assert job.watch_query_id == wq_id
    assert job.status == "running"
    assert job.started_at is not None
    assert job.completed_at is None
    assert job.error_message is None


async def test_update_scrape_job_success(db_session: AsyncSession):
    """Updates job status to 'success' and sets completed_at."""
    wq_id, _ = await _create_prerequisites(db_session)
    job = await create_scrape_job(db_session, wq_id)

    updated = await update_scrape_job(db_session, job, status="success")

    assert updated.status == "success"
    assert updated.completed_at is not None
    assert updated.error_message is None


async def test_update_scrape_job_failed(db_session: AsyncSession):
    """Updates job status to 'failed' with error_message and completed_at."""
    wq_id, _ = await _create_prerequisites(db_session)
    job = await create_scrape_job(db_session, wq_id)

    updated = await update_scrape_job(
        db_session, job, status="failed", error_message="Something went wrong"
    )

    assert updated.status == "failed"
    assert updated.completed_at is not None
    assert updated.error_message == "Something went wrong"


async def test_create_scrape_result(db_session: AsyncSession):
    """Creates ScrapeResult with all 6 required fields, returns object with id and created_at."""
    wq_id, ru_id = await _create_prerequisites(db_session)
    job = await create_scrape_job(db_session, wq_id)

    result = await create_scrape_result(
        db_session,
        retailer_url_id=ru_id,
        scrape_job_id=job.id,
        product_name="Test Product",
        price_cents=1999,
        listing_url="https://amazon.com/dp/test",
        retailer_name="Amazon",
    )

    assert result.id is not None
    assert result.retailer_url_id == ru_id
    assert result.scrape_job_id == job.id
    assert result.product_name == "Test Product"
    assert result.price_cents == 1999
    assert result.listing_url == "https://amazon.com/dp/test"
    assert result.retailer_name == "Amazon"
    assert result.created_at is not None


async def test_scrape_result_immutable(db_session: AsyncSession):
    """ScrapeResult has no updated_at field (only created_at)."""
    assert not hasattr(ScrapeResult, "updated_at")
    assert hasattr(ScrapeResult, "created_at")


async def test_get_latest_scrape_result(db_session: AsyncSession):
    """Returns most recent ScrapeResult for a given retailer_url_id."""
    wq_id, ru_id = await _create_prerequisites(db_session)
    job = await create_scrape_job(db_session, wq_id)

    # Create two results for the same retailer URL
    await create_scrape_result(
        db_session,
        retailer_url_id=ru_id,
        scrape_job_id=job.id,
        product_name="First",
        price_cents=1000,
        listing_url="https://amazon.com/dp/test",
        retailer_name="Amazon",
    )
    second = await create_scrape_result(
        db_session,
        retailer_url_id=ru_id,
        scrape_job_id=job.id,
        product_name="Second",
        price_cents=2000,
        listing_url="https://amazon.com/dp/test",
        retailer_name="Amazon",
    )

    latest = await get_latest_scrape_result(db_session, ru_id)

    assert latest is not None
    assert latest.id == second.id
    assert latest.product_name == "Second"
    assert latest.price_cents == 2000


async def _make_scrape_result(db, retailer_url_id, scrape_job_id, price_cents, created_at=None):
    """Helper: create a ScrapeResult with optional created_at override."""
    sr = ScrapeResult(
        retailer_url_id=retailer_url_id,
        scrape_job_id=scrape_job_id,
        product_name="Test Product",
        price_cents=price_cents,
        listing_url="https://example.com/product",
        retailer_name="Example",
    )
    if created_at is not None:
        sr.created_at = created_at
    db.add(sr)
    await db.flush()
    return sr


class TestRollingAvg:
    @pytest.mark.asyncio
    async def test_correct_avg_and_count(self, db_session):
        """Returns correct average and count for results within 30-day window."""
        wq_id, ru_id = await _create_prerequisites(db_session)
        job = await create_scrape_job(db_session, wq_id)
        now = datetime.utcnow()

        # Create 3 results within 30-day window: 1000, 1200, 800 -> avg=1000, count=3
        for price, offset_days in [(1000, 5), (1200, 10), (800, 15)]:
            await _make_scrape_result(db_session, ru_id, job.id, price, now - timedelta(days=offset_days))

        avg, count = await get_rolling_avg_price(db_session, ru_id)
        assert count == 3
        assert avg == 1000

    @pytest.mark.asyncio
    async def test_excludes_old_results(self, db_session):
        """Results older than 30 days are excluded from the average."""
        wq_id, ru_id = await _create_prerequisites(db_session)
        job = await create_scrape_job(db_session, wq_id)
        now = datetime.utcnow()

        # One result within window, one outside
        await _make_scrape_result(db_session, ru_id, job.id, 1000, now - timedelta(days=5))
        await _make_scrape_result(db_session, ru_id, job.id, 2000, now - timedelta(days=35))

        avg, count = await get_rolling_avg_price(db_session, ru_id)
        assert count == 1
        assert avg == 1000

    @pytest.mark.asyncio
    async def test_no_results(self, db_session):
        """Returns (None, 0) when no results exist."""
        wq_id, ru_id = await _create_prerequisites(db_session)

        avg, count = await get_rolling_avg_price(db_session, ru_id)
        assert avg is None
        assert count == 0


class TestAllTimeLow:
    @pytest.mark.asyncio
    async def test_returns_min_across_urls(self, db_session):
        """Returns minimum price across all retailer URLs for a watch query."""
        wq = WatchQuery(name="Test", threshold_cents=5000)
        db_session.add(wq)
        await db_session.flush()

        ru1 = RetailerUrl(watch_query_id=wq.id, url="https://store1.com/product")
        ru2 = RetailerUrl(watch_query_id=wq.id, url="https://store2.com/product")
        db_session.add_all([ru1, ru2])
        await db_session.flush()

        job = ScrapeJob(watch_query_id=wq.id, status="success", started_at=datetime.utcnow())
        db_session.add(job)
        await db_session.flush()

        await _make_scrape_result(db_session, ru1.id, job.id, 1500)
        await _make_scrape_result(db_session, ru2.id, job.id, 1200)

        min_price = await get_all_time_min_price(db_session, wq.id)
        assert min_price == 1200

    @pytest.mark.asyncio
    async def test_no_results(self, db_session):
        """Returns None when no results exist."""
        wq = WatchQuery(name="Test", threshold_cents=5000)
        db_session.add(wq)
        await db_session.flush()

        min_price = await get_all_time_min_price(db_session, wq.id)
        assert min_price is None


class TestIsWithinCooldown:
    @pytest.mark.asyncio
    async def test_within_cooldown(self, db_session):
        """Returns True when last alert is within cooldown window."""
        wq = WatchQuery(name="Test", threshold_cents=5000)
        db_session.add(wq)
        await db_session.flush()

        ru = RetailerUrl(watch_query_id=wq.id, url="https://store.com/p")
        db_session.add(ru)
        await db_session.flush()

        job = ScrapeJob(watch_query_id=wq.id, status="success", started_at=datetime.utcnow())
        db_session.add(job)
        await db_session.flush()

        sr = await _make_scrape_result(db_session, ru.id, job.id, 1000)
        alert = Alert(scrape_result_id=sr.id, watch_query_id=wq.id)
        db_session.add(alert)
        await db_session.flush()

        result = await is_within_cooldown(db_session, wq.id, 24)
        assert result is True

    @pytest.mark.asyncio
    async def test_cooldown_expired(self, db_session):
        """Returns False when last alert is older than cooldown window."""
        wq = WatchQuery(name="Test", threshold_cents=5000)
        db_session.add(wq)
        await db_session.flush()

        ru = RetailerUrl(watch_query_id=wq.id, url="https://store.com/p")
        db_session.add(ru)
        await db_session.flush()

        job = ScrapeJob(watch_query_id=wq.id, status="success", started_at=datetime.utcnow())
        db_session.add(job)
        await db_session.flush()

        sr = await _make_scrape_result(db_session, ru.id, job.id, 1000)
        alert = Alert(scrape_result_id=sr.id, watch_query_id=wq.id)
        alert.created_at = datetime.utcnow() - timedelta(hours=25)
        db_session.add(alert)
        await db_session.flush()

        result = await is_within_cooldown(db_session, wq.id, 24)
        assert result is False

    @pytest.mark.asyncio
    async def test_no_alerts(self, db_session):
        """Returns False when no alerts exist."""
        wq = WatchQuery(name="Test", threshold_cents=5000)
        db_session.add(wq)
        await db_session.flush()

        result = await is_within_cooldown(db_session, wq.id, 24)
        assert result is False
