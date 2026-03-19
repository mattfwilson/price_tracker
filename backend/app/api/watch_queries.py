"""Watch query CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.retailer_url import RetailerUrl
from app.repositories.scrape_result import get_latest_scrape_result
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
    for url_obj in query.retailer_urls:
        latest = await get_latest_scrape_result(db, url_obj.id)
        latest_data = None
        if latest is not None:
            delta = await calculate_price_delta(db, url_obj.id, latest.price_cents)
            latest_data = LatestScrapeResult(
                product_name=latest.product_name,
                price_cents=latest.price_cents,
                listing_url=latest.listing_url,
                scraped_at=latest.created_at,
                **delta,
            )
        urls_with_latest.append(
            RetailerUrlWithLatest(
                id=url_obj.id,
                url=url_obj.url,
                created_at=url_obj.created_at,
                latest_result=latest_data,
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
        # Reload to get fresh retailer_urls
        query = await get_watch_query(db, query_id)

    return query


@router.delete("/{query_id}", status_code=204)
async def delete_query(query_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a watch query."""
    deleted = await delete_watch_query(db, query_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watch query not found")
