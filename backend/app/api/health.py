"""Scrape health dashboard API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.scrape_url_attempt import get_health_stats_for_all_urls
from app.schemas.health import HealthListResponse, UrlHealthResponse

router = APIRouter(prefix="/scrape-health", tags=["scrape-health"])


@router.get("/urls", response_model=HealthListResponse)
async def list_url_health(db: AsyncSession = Depends(get_db)) -> HealthListResponse:
    """Return health stats for all retailer URLs that have recorded attempts."""
    stats = await get_health_stats_for_all_urls(db)
    return HealthListResponse(urls=[UrlHealthResponse(**row) for row in stats])


@router.get("/query/{watch_query_id}", response_model=HealthListResponse)
async def get_query_health(
    watch_query_id: int,
    db: AsyncSession = Depends(get_db),
) -> HealthListResponse:
    """Return health stats filtered to a single watch query's URLs.

    Used by QueryCard in Plan 03 to embed health indicators in detail requests.
    """
    stats = await get_health_stats_for_all_urls(db)
    filtered = [row for row in stats if row["watch_query_id"] == watch_query_id]
    return HealthListResponse(urls=[UrlHealthResponse(**row) for row in filtered])
