"""Watch query CRUD API endpoints."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.retailer_url import RetailerUrl
from app.repositories.scrape_result import (
    get_all_time_extremes_for_url,
    get_last_price_change_result,
    get_latest_scrape_result,
    get_price_near_date,
    get_rolling_avg_price,
)
from app.repositories.watch_query import (
    create_watch_query,
    delete_watch_query,
    get_watch_query,
    list_watch_queries,
    update_watch_query,
)
from app.schemas.watch_query import (
    LatestScrapeResult,
    RetailerUrlWithLatest,
    WatchQueryCreate,
    WatchQueryDetailResponse,
    WatchQueryResponse,
    WatchQueryUpdate,
)
from app.services.scrape_service import calculate_price_delta

router = APIRouter(prefix="/watch-queries", tags=["watch-queries"])


@router.post("/", response_model=WatchQueryResponse, status_code=201)
async def create(payload: WatchQueryCreate, db: AsyncSession = Depends(get_db)):
    """Create a new watch query with associated retailer URLs."""
    unique_urls = list(dict.fromkeys(payload.urls))
    query = await create_watch_query(
        db,
        name=payload.name,
        threshold_cents=payload.threshold_cents,
        urls=unique_urls,
    )

    # Register scheduler job for the new active query
    from app.services.scheduler import add_scrape_job
    if query.is_active:
        add_scrape_job(query.id, query.schedule)

    return query


@router.get("/", response_model=list[WatchQueryResponse])
async def list_queries(db: AsyncSession = Depends(get_db)):
    """List all watch queries."""
    queries = await list_watch_queries(db)
    return queries


@router.get("/{query_id}", response_model=WatchQueryDetailResponse)
async def get_query(query_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single watch query with embedded latest scrape results."""
    query = await get_watch_query(db, query_id)
    if query is None:
        raise HTTPException(status_code=404, detail="Watch query not found")

    # Build response with latest scrape results embedded per retailer URL
    urls_with_latest = []
    now = datetime.utcnow()
    target_30d = now - timedelta(days=30)
    target_90d = now - timedelta(days=90)
    for url_obj in query.retailer_urls:
        latest = await get_latest_scrape_result(db, url_obj.id)
        latest_data = None
        if latest is not None:
            # Find the last record with a different price to show the direction
            # of the most recent meaningful price movement. Comparing against the
            # immediately previous record would always return "unchanged" when
            # consecutive scrapes return the same price, hiding the real trend.
            prev = await get_last_price_change_result(db, url_obj.id, latest.price_cents)
            if prev is not None:
                delta = await calculate_price_delta(
                    db, url_obj.id, latest.price_cents,
                    previous_price_cents=prev.price_cents,
                )
            else:
                delta = {"direction": "new", "delta_cents": 0, "pct_change": 0.0}
            latest_data = LatestScrapeResult(
                product_name=latest.product_name,
                price_cents=latest.price_cents,
                listing_url=latest.listing_url,
                scraped_at=latest.created_at,
                **delta,
            )
        # Wayback stats per retailer URL (per D-04)
        price_30d, date_30d = await get_price_near_date(db, url_obj.id, target_30d)
        price_90d, date_90d = await get_price_near_date(db, url_obj.id, target_90d)
        avg_30d, count_30d = await get_rolling_avg_price(db, url_obj.id, window_days=30)
        avg_90d, count_90d = await get_rolling_avg_price(db, url_obj.id, window_days=90)
        atl, ath = await get_all_time_extremes_for_url(db, url_obj.id)
        urls_with_latest.append(
            RetailerUrlWithLatest(
                id=url_obj.id,
                url=url_obj.url,
                created_at=url_obj.created_at,
                latest_result=latest_data,
                price_30d_cents=price_30d,
                date_30d=date_30d,
                price_90d_cents=price_90d,
                date_90d=date_90d,
                avg_30d_cents=avg_30d,
                avg_30d_count=count_30d,
                avg_90d_cents=avg_90d,
                avg_90d_count=count_90d,
                all_time_low_cents=atl,
                all_time_high_cents=ath,
            )
        )

    return WatchQueryDetailResponse(
        id=query.id,
        name=query.name,
        threshold_cents=query.threshold_cents,
        is_active=query.is_active,
        schedule=query.schedule,
        retailer_urls=urls_with_latest,
        created_at=query.created_at,
        updated_at=query.updated_at,
    )


@router.patch("/{query_id}", response_model=WatchQueryResponse)
async def update_query(
    query_id: int, payload: WatchQueryUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a watch query's fields and optionally replace URLs."""
    # Update scalar fields via repository
    fields = payload.model_dump(exclude_unset=True, exclude={"urls"})
    query = await update_watch_query(db, query_id, **fields)
    if query is None:
        raise HTTPException(status_code=404, detail="Watch query not found")

    # Sync scheduler on pause/resume/schedule change
    from app.services.scheduler import add_scrape_job, remove_scrape_job
    if "is_active" in fields:
        if fields["is_active"]:
            add_scrape_job(query.id, query.schedule)
        else:
            remove_scrape_job(query.id)
    if "schedule" in fields and query.is_active:
        add_scrape_job(query.id, query.schedule)

    # Handle URL replacement if urls provided (diff-based to preserve history)
    if payload.urls is not None:
        unique_urls = list(dict.fromkeys(payload.urls))
        existing_urls = {url_obj.url: url_obj for url_obj in query.retailer_urls}
        new_url_set = set(unique_urls)

        # Delete URLs no longer present
        for url_str, url_obj in existing_urls.items():
            if url_str not in new_url_set:
                await db.delete(url_obj)

        # Add URLs not already present
        for url_str in unique_urls:
            if url_str not in existing_urls:
                db.add(RetailerUrl(url=url_str, watch_query_id=query.id))

        await db.flush()
        # Expire cached state so selectinload re-queries the DB
        db.expire(query)
        query = await get_watch_query(db, query_id)

    return query


@router.delete("/{query_id}", status_code=204)
async def delete_query(query_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a watch query."""
    from app.services.scheduler import remove_scrape_job
    remove_scrape_job(query_id)

    deleted = await delete_watch_query(db, query_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watch query not found")
