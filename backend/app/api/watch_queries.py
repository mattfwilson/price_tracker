"""Watch query CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.watch_query import (
    create_watch_query,
    delete_watch_query,
    get_watch_query,
    list_watch_queries,
    update_watch_query,
)
from app.schemas.watch_query import WatchQueryCreate, WatchQueryResponse

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
