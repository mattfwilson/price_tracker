"""Tests for ScrapeResult and ScrapeJob repository operations."""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scrape_result import ScrapeResult
from app.models.watch_query import WatchQuery
from app.models.retailer_url import RetailerUrl
from app.repositories.scrape_result import (
    create_scrape_job,
    create_scrape_result,
    get_latest_scrape_result,
    get_rolling_avg_price,
    get_all_time_min_price,
    get_price_near_date,
    get_all_time_extremes_for_url,
    update_scrape_job,
)


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


async def _make_scrape_result(
    db: AsyncSession,
    retailer_url_id: int,
    scrape_job_id: int,
    price_cents: int,
    created_at: datetime | None = None,
) -> ScrapeResult:
    """Helper: create a ScrapeResult with optional created_at override."""
    result = ScrapeResult(
        retailer_url_id=retailer_url_id,
        scrape_job_id=scrape_job_id,
        product_name="Test Product",
        price_cents=price_cents,
        listing_url="https://amazon.com/dp/test",
        retailer_name="Amazon",
    )
    if created_at is not None:
        result.created_at = created_at
    db.add(result)
    await db.flush()
    return result


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


class TestRollingAvg:
    """Tests for get_rolling_avg_price."""

    async def test_returns_avg_within_window(self, db_session: AsyncSession):
        """Results within window are included in average."""
        wq_id, ru_id = await _create_prerequisites(db_session)
        job = await create_scrape_job(db_session, wq_id)
        now = datetime.utcnow()

        await _make_scrape_result(db_session, ru_id, job.id, 1000, now - timedelta(days=5))
        await _make_scrape_result(db_session, ru_id, job.id, 2000, now - timedelta(days=10))
        # Outside 30-day window
        await _make_scrape_result(db_session, ru_id, job.id, 9999, now - timedelta(days=40))

        avg, count = await get_rolling_avg_price(db_session, ru_id, window_days=30)

        assert count == 2
        assert avg == 1500  # (1000 + 2000) / 2

    async def test_no_results(self, db_session: AsyncSession):
        """No results returns (None, 0)."""
        wq_id, ru_id = await _create_prerequisites(db_session)

        avg, count = await get_rolling_avg_price(db_session, ru_id, window_days=30)

        assert avg is None
        assert count == 0

    async def test_90_day_window(self, db_session: AsyncSession):
        """Results at -10d, -50d, -80d with window_days=90 returns all three; window_days=30 returns only 1."""
        wq_id, ru_id = await _create_prerequisites(db_session)
        job = await create_scrape_job(db_session, wq_id)
        now = datetime.utcnow()

        await _make_scrape_result(db_session, ru_id, job.id, 1000, now - timedelta(days=10))
        await _make_scrape_result(db_session, ru_id, job.id, 2000, now - timedelta(days=50))
        await _make_scrape_result(db_session, ru_id, job.id, 3000, now - timedelta(days=80))

        avg_90, count_90 = await get_rolling_avg_price(db_session, ru_id, window_days=90)
        avg_30, count_30 = await get_rolling_avg_price(db_session, ru_id, window_days=30)

        assert count_90 == 3
        assert avg_90 == 2000  # (1000 + 2000 + 3000) / 3
        assert count_30 == 1
        assert avg_30 == 1000


class TestPriceNearDate:
    """Tests for get_price_near_date."""

    async def test_returns_nearest_result(self, db_session: AsyncSession):
        """Returns the result nearest to target_date within the proximity window."""
        wq_id, ru_id = await _create_prerequisites(db_session)
        job = await create_scrape_job(db_session, wq_id)
        now = datetime.utcnow()
        target = now - timedelta(days=30)

        # Create results at -28d (closer to target) and -32d (farther)
        closer = await _make_scrape_result(db_session, ru_id, job.id, 1500, now - timedelta(days=28))
        await _make_scrape_result(db_session, ru_id, job.id, 2000, now - timedelta(days=32))

        price, actual_date = await get_price_near_date(db_session, ru_id, target, max_delta_days=7)

        assert price == closer.price_cents
        assert actual_date is not None

    async def test_returns_none_outside_window(self, db_session: AsyncSession):
        """Returns (None, None) when result is outside the proximity window."""
        wq_id, ru_id = await _create_prerequisites(db_session)
        job = await create_scrape_job(db_session, wq_id)
        now = datetime.utcnow()
        target = now - timedelta(days=30)

        # Result at -45d is outside window of -37d to -23d
        await _make_scrape_result(db_session, ru_id, job.id, 1500, now - timedelta(days=45))

        price, actual_date = await get_price_near_date(db_session, ru_id, target, max_delta_days=7)

        assert price is None
        assert actual_date is None

    async def test_exact_match(self, db_session: AsyncSession):
        """Returns the exact result when it matches target_date exactly."""
        wq_id, ru_id = await _create_prerequisites(db_session)
        job = await create_scrape_job(db_session, wq_id)
        now = datetime.utcnow()
        target = now - timedelta(days=30)

        exact = await _make_scrape_result(db_session, ru_id, job.id, 1234, target)

        price, actual_date = await get_price_near_date(db_session, ru_id, target, max_delta_days=7)

        assert price == exact.price_cents
        assert actual_date is not None

    async def test_no_results(self, db_session: AsyncSession):
        """Returns (None, None) when no scrape results exist."""
        wq_id, ru_id = await _create_prerequisites(db_session)
        now = datetime.utcnow()
        target = now - timedelta(days=30)

        price, actual_date = await get_price_near_date(db_session, ru_id, target, max_delta_days=7)

        assert price is None
        assert actual_date is None


class TestAllTimeExtremes:
    """Tests for get_all_time_extremes_for_url."""

    async def test_returns_min_and_max(self, db_session: AsyncSession):
        """Returns (800, 2000) for prices [1000, 1500, 800, 2000]."""
        wq_id, ru_id = await _create_prerequisites(db_session)
        job = await create_scrape_job(db_session, wq_id)

        for price in [1000, 1500, 800, 2000]:
            await _make_scrape_result(db_session, ru_id, job.id, price)

        low, high = await get_all_time_extremes_for_url(db_session, ru_id)

        assert low == 800
        assert high == 2000

    async def test_no_results(self, db_session: AsyncSession):
        """Returns (None, None) when no scrape results exist."""
        wq_id, ru_id = await _create_prerequisites(db_session)

        low, high = await get_all_time_extremes_for_url(db_session, ru_id)

        assert low is None
        assert high is None

    async def test_single_result(self, db_session: AsyncSession):
        """Returns (1500, 1500) for a single result."""
        wq_id, ru_id = await _create_prerequisites(db_session)
        job = await create_scrape_job(db_session, wq_id)

        await _make_scrape_result(db_session, ru_id, job.id, 1500)

        low, high = await get_all_time_extremes_for_url(db_session, ru_id)

        assert low == 1500
        assert high == 1500
