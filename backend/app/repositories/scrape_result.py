"""CRUD operations for scrape results and scrape jobs."""

from datetime import datetime

from sqlalchemy import select
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
