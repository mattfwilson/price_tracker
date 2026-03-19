"""Tests for ScrapeResult and ScrapeJob repository operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scrape_result import ScrapeResult
from app.models.watch_query import WatchQuery
from app.models.retailer_url import RetailerUrl
from app.repositories.scrape_result import (
    create_scrape_job,
    create_scrape_result,
    get_latest_scrape_result,
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
