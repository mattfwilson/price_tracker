"""Tests for scrape service orchestration (run_scrape_job)."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retailer_url import RetailerUrl
from app.models.scrape_result import ScrapeResult
from app.models.watch_query import WatchQuery
from app.scrapers.base import FailureType, ScrapeData, ScrapeError
from app.services.scrape_service import run_scrape_job


async def _setup_watch_query(db: AsyncSession, urls: list[str]) -> int:
    """Create a WatchQuery with RetailerUrls, return watch_query_id."""
    wq = WatchQuery(name="Test Query", threshold_cents=2000)
    db.add(wq)
    await db.flush()
    for url in urls:
        ru = RetailerUrl(watch_query_id=wq.id, url=url)
        db.add(ru)
    await db.flush()
    return wq.id


def _make_scrape_data(url: str, name: str = "Product", price: int = 1999) -> ScrapeData:
    return ScrapeData(
        product_name=name,
        price_cents=price,
        listing_url=url,
        retailer_name="TestRetailer",
    )


@pytest.mark.asyncio
async def test_run_scrape_job_all_success(db_session: AsyncSession):
    """2 URLs both succeed -> job.status == 'success', 2 ScrapeResult records."""
    urls = ["https://a.com/product1", "https://b.com/product2"]
    wq_id = await _setup_watch_query(db_session, urls)

    async def mock_scrape(browser, url):
        return _make_scrape_data(url, name=f"Product for {url}")

    with patch(
        "app.services.scrape_service.scrape_single_url", side_effect=mock_scrape
    ):
        job = await run_scrape_job(db_session, wq_id, AsyncMock())

    assert job.status == "success"
    assert job.error_message is None

    # Verify 2 ScrapeResult records created
    stmt = select(ScrapeResult).where(ScrapeResult.scrape_job_id == job.id)
    result = await db_session.execute(stmt)
    results = list(result.scalars().all())
    assert len(results) == 2


@pytest.mark.asyncio
async def test_run_scrape_job_all_fail(db_session: AsyncSession):
    """2 URLs both fail -> job.status == 'failed', 0 results, error_message has both URLs."""
    urls = ["https://a.com/product1", "https://b.com/product2"]
    wq_id = await _setup_watch_query(db_session, urls)

    async def mock_scrape(browser, url):
        raise ScrapeError(FailureType.BLOCKED, f"blocked on {url}")

    with patch(
        "app.services.scrape_service.scrape_single_url", side_effect=mock_scrape
    ):
        job = await run_scrape_job(db_session, wq_id, AsyncMock())

    assert job.status == "failed"
    assert "a.com" in job.error_message
    assert "b.com" in job.error_message

    # Verify 0 ScrapeResult records
    stmt = select(ScrapeResult).where(ScrapeResult.scrape_job_id == job.id)
    result = await db_session.execute(stmt)
    assert len(list(result.scalars().all())) == 0


@pytest.mark.asyncio
async def test_run_scrape_job_partial(db_session: AsyncSession):
    """First URL succeeds, second fails -> job.status == 'partial_success', 1 result."""
    urls = ["https://a.com/product1", "https://b.com/product2"]
    wq_id = await _setup_watch_query(db_session, urls)

    call_count = 0

    async def mock_scrape(browser, url):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_scrape_data(url)
        raise ScrapeError(FailureType.NETWORK_ERROR, "timeout")

    with patch(
        "app.services.scrape_service.scrape_single_url", side_effect=mock_scrape
    ):
        job = await run_scrape_job(db_session, wq_id, AsyncMock())

    assert job.status == "partial_success"
    assert job.error_message is not None

    # Verify 1 ScrapeResult record
    stmt = select(ScrapeResult).where(ScrapeResult.scrape_job_id == job.id)
    result = await db_session.execute(stmt)
    assert len(list(result.scalars().all())) == 1


@pytest.mark.asyncio
async def test_run_scrape_job_sets_timestamps(db_session: AsyncSession):
    """Job has started_at and completed_at set."""
    urls = ["https://a.com/product1"]
    wq_id = await _setup_watch_query(db_session, urls)

    async def mock_scrape(browser, url):
        return _make_scrape_data(url)

    with patch(
        "app.services.scrape_service.scrape_single_url", side_effect=mock_scrape
    ):
        job = await run_scrape_job(db_session, wq_id, AsyncMock())

    assert job.started_at is not None
    assert job.completed_at is not None
    assert job.completed_at >= job.started_at


@pytest.mark.asyncio
async def test_run_scrape_job_human_delay(db_session: AsyncSession):
    """scrape_single_url is called (mocked) -- verify the orchestrator invokes it for each URL."""
    urls = ["https://a.com/product1", "https://b.com/product2"]
    wq_id = await _setup_watch_query(db_session, urls)

    scrape_mock = AsyncMock(side_effect=lambda b, u: _make_scrape_data(u))

    with patch(
        "app.services.scrape_service.scrape_single_url", side_effect=scrape_mock
    ):
        job = await run_scrape_job(db_session, wq_id, AsyncMock())

    assert job.status == "success"
    assert scrape_mock.call_count == 2
