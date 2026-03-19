"""Alert CRUD API endpoints with SSE streaming."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.alert import (
    dismiss_all_alerts,
    get_unread_count,
    list_alerts,
    mark_alert_read,
)
from app.schemas.alert import AlertResponse, UnreadCountResponse
from app.services.alert_service import add_sse_client, remove_sse_client

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=list[AlertResponse])
async def list_all_alerts(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all alerts with joined watch query and scrape result data."""
    alerts = await list_alerts(db, limit=limit, offset=offset)
    return [
        AlertResponse(
            id=a.id,
            watch_query_id=a.watch_query_id,
            watch_query_name=a.watch_query.name,
            product_name=a.scrape_result.product_name,
            price_cents=a.scrape_result.price_cents,
            retailer_name=a.scrape_result.retailer_name,
            listing_url=a.scrape_result.listing_url,
            is_read=a.is_read,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(db: AsyncSession = Depends(get_db)):
    """Get current unread alert count."""
    count = await get_unread_count(db)
    return UnreadCountResponse(unread_count=count)


@router.patch("/{alert_id}/read", response_model=AlertResponse)
async def mark_read(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a single alert as read."""
    alert = await mark_alert_read(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    # Eager-load relationships for response
    await db.refresh(alert, ["watch_query", "scrape_result"])
    return AlertResponse(
        id=alert.id,
        watch_query_id=alert.watch_query_id,
        watch_query_name=alert.watch_query.name,
        product_name=alert.scrape_result.product_name,
        price_cents=alert.scrape_result.price_cents,
        retailer_name=alert.scrape_result.retailer_name,
        listing_url=alert.scrape_result.listing_url,
        is_read=alert.is_read,
        created_at=alert.created_at,
    )


@router.post("/dismiss-all")
async def dismiss_all(db: AsyncSession = Depends(get_db)):
    """Mark all unread alerts as read. Returns count of dismissed alerts."""
    count = await dismiss_all_alerts(db)
    return {"dismissed_count": count}


@router.get("/stream")
async def alert_stream(request: Request):
    """SSE endpoint for real-time alert notifications."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    add_sse_client(queue)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    json_data = json.dumps(data, default=str)
                    yield f"event: alert\ndata: {json_data}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent connection timeout
                    yield ": keepalive\n\n"
        finally:
            remove_sse_client(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
