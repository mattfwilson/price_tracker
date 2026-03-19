"""Scrape and price history API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.scrape_result import ScrapeResult
from app.repositories.watch_query import get_watch_query
from app.schemas.scrape import (
    HistoryRecordResponse,
    ScrapeJobResponse,
    ScrapeResultResponse,
)
from app.scrapers.browser import BrowserManager
from app.services.scrape_service import calculate_price_delta, run_scrape_job

router = APIRouter(tags=["scrapes"])

# Lazy singleton BrowserManager -- not started at app boot
_browser_manager: BrowserManager | None = None


async def get_browser_manager() -> BrowserManager:
    """Return a lazily initialized BrowserManager singleton."""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
        await _browser_manager.start()
    return _browser_manager


@router.post("/watch-queries/{query_id}/scrape", response_model=ScrapeJobResponse)
async def trigger_scrape(query_id: int, db: AsyncSession = Depends(get_db)):
    """Trigger an on-demand scrape for a watch query and return results with price deltas."""
    query = await get_watch_query(db, query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="Watch query not found")

    bm = await get_browser_manager()
    job = await run_scrape_job(db, query_id, bm)

    # Load job's scrape results with eager loading
    await db.refresh(job, attribute_names=["scrape_results"])

    # Build response with price deltas for each result.
    # Since the new results are already flushed to DB, get_latest_scrape_result
    # would find the result we just created. Instead, query for the second-latest
    # result (the one before this scrape) to compute the delta correctly.
    results = []
    for sr in job.scrape_results:
        # Find the previous result (before the one just created) for this retailer_url
        prev_stmt = (
            select(ScrapeResult)
            .where(ScrapeResult.retailer_url_id == sr.retailer_url_id)
            .where(ScrapeResult.id != sr.id)
            .order_by(ScrapeResult.created_at.desc(), ScrapeResult.id.desc())
            .limit(1)
        )
        prev_result = await db.execute(prev_stmt)
        prev_record = prev_result.scalar_one_or_none()
        if prev_record is not None:
            delta = await calculate_price_delta(
                db, sr.retailer_url_id, sr.price_cents,
                previous_price_cents=prev_record.price_cents,
            )
        else:
            # First-ever scrape for this retailer URL
            delta = {"direction": "new", "delta_cents": 0, "pct_change": 0.0}
        results.append(
            ScrapeResultResponse(
                product_name=sr.product_name,
                price_cents=sr.price_cents,
                retailer_name=sr.retailer_name,
                listing_url=sr.listing_url,
                scraped_at=sr.created_at,
                **delta,
            )
        )

    return ScrapeJobResponse(
        job_id=job.id,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        results=results,
    )


@router.get(
    "/retailer-urls/{retailer_url_id}/history",
    response_model=list[HistoryRecordResponse],
)
async def get_history(retailer_url_id: int, db: AsyncSession = Depends(get_db)):
    """Get price history for a retailer URL, newest-first, with computed deltas."""
    stmt = (
        select(ScrapeResult)
        .where(ScrapeResult.retailer_url_id == retailer_url_id)
        .order_by(ScrapeResult.created_at.desc(), ScrapeResult.id.desc())
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    if not records:
        return []

    # Compute deltas using calculate_price_delta() per locked user decision.
    # Records are newest-first. For each record, pass the previous (older) record's
    # price_cents via the previous_price_cents parameter so calculate_price_delta()
    # compares consecutive pairs without a DB lookup.
    # The oldest record has no previous record in the series, so it is marked "new".
    history = []
    for i, rec in enumerate(records):
        if i < len(records) - 1:
            # Previous record exists (the one right after in the list = older)
            prev_price = records[i + 1].price_cents
            delta = await calculate_price_delta(
                db,
                retailer_url_id,
                rec.price_cents,
                previous_price_cents=prev_price,
            )
        else:
            # Oldest record -- no previous in the series; this is the first-ever scrape
            delta = {"direction": "new", "delta_cents": 0, "pct_change": 0.0}

        history.append(
            HistoryRecordResponse(
                id=rec.id,
                product_name=rec.product_name,
                price_cents=rec.price_cents,
                retailer_name=rec.retailer_name,
                listing_url=rec.listing_url,
                scraped_at=rec.created_at,
                **delta,
            )
        )

    return history
