"""Alert evaluation service with re-breach detection and SSE broadcast stub."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.scrape_result import ScrapeResult
from app.models.watch_query import WatchQuery
from app.repositories.alert import create_alert, get_unread_count

logger = logging.getLogger(__name__)

# SSE client queues -- used by Plan 03 (SSE endpoints)
_sse_clients: set[asyncio.Queue] = set()


def add_sse_client(queue: asyncio.Queue) -> None:
    """Register an SSE client queue."""
    _sse_clients.add(queue)


def remove_sse_client(queue: asyncio.Queue) -> None:
    """Unregister an SSE client queue."""
    _sse_clients.discard(queue)


async def broadcast_alert(event_data: dict) -> None:
    """Push event_data to all connected SSE clients."""
    for queue in _sse_clients.copy():
        try:
            queue.put_nowait(event_data)
        except asyncio.QueueFull:
            logger.warning("SSE client queue full, dropping alert event")


async def should_fire_alert(
    session: AsyncSession,
    retailer_url_id: int,
    current_price_cents: int,
    threshold_cents: int,
) -> bool:
    """Determine if an alert should fire for the current price.

    Logic:
    - If current_price_cents > threshold_cents: no alert
    - If no previous result: first-ever scrape, new breach -> alert
    - If previous was also at/below threshold: continued breach -> no alert
    - If previous was above threshold: re-breach -> alert
    """
    if current_price_cents > threshold_cents:
        return False

    # Query previous ScrapeResult for this retailer_url_id.
    # offset(1) skips the current result that was just flushed.
    stmt = (
        select(ScrapeResult)
        .where(ScrapeResult.retailer_url_id == retailer_url_id)
        .order_by(ScrapeResult.created_at.desc(), ScrapeResult.id.desc())
        .offset(1)
        .limit(1)
    )
    result = await session.execute(stmt)
    previous = result.scalar_one_or_none()

    if previous is None:
        # First-ever scrape for this retailer URL
        return True

    if previous.price_cents <= threshold_cents:
        # Continued breach -- previous was also at/below threshold
        return False

    # Re-breach: previous was above threshold, current is at/below
    return True


async def evaluate_alerts_for_job(
    session: AsyncSession,
    watch_query_id: int,
    scrape_job_id: int,
) -> list[Alert]:
    """Evaluate all scrape results from a job and create alerts for threshold breaches.

    Returns list of created Alert records.
    """
    # Load WatchQuery
    stmt = select(WatchQuery).where(WatchQuery.id == watch_query_id)
    result = await session.execute(stmt)
    wq = result.scalar_one_or_none()
    if wq is None:
        return []

    # Query all ScrapeResults for this job
    stmt = select(ScrapeResult).where(ScrapeResult.scrape_job_id == scrape_job_id)
    result = await session.execute(stmt)
    scrape_results = list(result.scalars().all())

    created_alerts: list[Alert] = []
    for sr in scrape_results:
        if await should_fire_alert(session, sr.retailer_url_id, sr.price_cents, wq.threshold_cents):
            alert = await create_alert(session, sr.id, watch_query_id)
            created_alerts.append(alert)

            # Build SSE payload and broadcast
            unread = await get_unread_count(session)
            payload = {
                "alert_id": alert.id,
                "watch_query_id": watch_query_id,
                "watch_query_name": wq.name,
                "product_name": sr.product_name,
                "price_cents": sr.price_cents,
                "retailer_name": sr.retailer_name,
                "listing_url": sr.listing_url,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
                "unread_count": unread,
            }
            await broadcast_alert(payload)

    return created_alerts
