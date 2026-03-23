"""CRUD operations for scrape results and scrape jobs."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scrape_job import ScrapeJob
from app.models.scrape_result import ScrapeResult


async def create_scrape_job(
    session: AsyncSession, watch_query_id: int
) -> ScrapeJob:
    """Create a new scrape job with status='running' and started_at=now."""
    job = ScrapeJob(
        watch_query_id=watch_query_id,
        status="running",
        started_at=datetime.utcnow(),
    )
    session.add(job)
    await session.flush()
    return job


async def update_scrape_job(
    session: AsyncSession,
    job: ScrapeJob,
    status: str,
    error_message: str | None = None,
) -> ScrapeJob:
    """Update job status, set completed_at, optionally set error_message."""
    job.status = status
    job.completed_at = datetime.utcnow()
    if error_message is not None:
        job.error_message = error_message
    await session.flush()
    return job


async def create_scrape_result(
    session: AsyncSession,
    retailer_url_id: int,
    scrape_job_id: int,
    product_name: str,
    price_cents: int,
    listing_url: str,
    retailer_name: str,
) -> ScrapeResult:
    """Create an immutable scrape result record."""
    result = ScrapeResult(
        retailer_url_id=retailer_url_id,
        scrape_job_id=scrape_job_id,
        product_name=product_name,
        price_cents=price_cents,
        listing_url=listing_url,
        retailer_name=retailer_name,
    )
    session.add(result)
    await session.flush()
    return result


async def get_latest_scrape_result(
    session: AsyncSession,
    retailer_url_id: int,
) -> ScrapeResult | None:
    """Get most recent scrape result for a retailer URL."""
    stmt = (
        select(ScrapeResult)
        .where(ScrapeResult.retailer_url_id == retailer_url_id)
        .order_by(ScrapeResult.created_at.desc(), ScrapeResult.id.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_last_price_change_result(
    session: AsyncSession,
    retailer_url_id: int,
    current_price_cents: int,
) -> ScrapeResult | None:
    """Get the most recent scrape result whose price differs from current_price_cents.

    Used by the dashboard to determine the direction and magnitude of the last
    meaningful price movement. Comparing against the immediately preceding record
    would show 'unchanged' whenever consecutive scrapes return the same price,
    masking the real trend. This query skips over same-price records to find the
    last time the price was actually different.
    """
    stmt = (
        select(ScrapeResult)
        .where(ScrapeResult.retailer_url_id == retailer_url_id)
        .where(ScrapeResult.price_cents != current_price_cents)
        .order_by(ScrapeResult.created_at.desc(), ScrapeResult.id.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_rolling_avg_price(
    session: AsyncSession, retailer_url_id: int, window_days: int = 30
) -> tuple[int | None, int]:
    """Return (avg_price_cents, count) for results within the rolling window."""
    cutoff = datetime.utcnow() - timedelta(days=window_days)
    stmt = select(
        func.avg(ScrapeResult.price_cents),
        func.count(ScrapeResult.id),
    ).where(
        ScrapeResult.retailer_url_id == retailer_url_id,
        ScrapeResult.created_at >= cutoff,
    )
    result = await session.execute(stmt)
    row = result.one()
    avg_raw, count = row[0], row[1]
    if count == 0:
        return None, 0
    return int(round(avg_raw)), count


async def get_all_time_min_price(
    session: AsyncSession, watch_query_id: int
) -> int | None:
    """Return the minimum price_cents across all retailer URLs for a watch query."""
    from app.models.retailer_url import RetailerUrl  # avoid circular import

    stmt = (
        select(func.min(ScrapeResult.price_cents))
        .join(RetailerUrl, ScrapeResult.retailer_url_id == RetailerUrl.id)
        .where(RetailerUrl.watch_query_id == watch_query_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_price_near_date(
    session: AsyncSession,
    retailer_url_id: int,
    target_date: datetime,
    max_delta_days: int = 7,
) -> tuple[int | None, datetime | None]:
    """Return (price_cents, actual_date) for the scrape result nearest to target_date.

    Searches within +/- max_delta_days of target_date.
    Returns (None, None) if no result found within the window.
    """
    window_start = target_date - timedelta(days=max_delta_days)
    window_end = target_date + timedelta(days=max_delta_days)
    stmt = (
        select(ScrapeResult.price_cents, ScrapeResult.created_at)
        .where(
            ScrapeResult.retailer_url_id == retailer_url_id,
            ScrapeResult.created_at >= window_start,
            ScrapeResult.created_at <= window_end,
        )
        .order_by(func.abs(func.julianday(ScrapeResult.created_at) - func.julianday(target_date)))
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None, None
    return row[0], row[1]


async def get_all_time_extremes_for_url(
    session: AsyncSession,
    retailer_url_id: int,
) -> tuple[int | None, int | None]:
    """Return (all_time_low_cents, all_time_high_cents) for a single retailer URL."""
    stmt = select(
        func.min(ScrapeResult.price_cents),
        func.max(ScrapeResult.price_cents),
    ).where(ScrapeResult.retailer_url_id == retailer_url_id)
    result = await session.execute(stmt)
    row = result.one()
    return row[0], row[1]
