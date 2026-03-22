"""Alert CRUD repository functions."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.alert import Alert


async def create_alert(
    session: AsyncSession, scrape_result_id: int, watch_query_id: int, alert_type: str = "threshold"
) -> Alert:
    """Create and flush (not commit) an Alert record."""
    alert = Alert(scrape_result_id=scrape_result_id, watch_query_id=watch_query_id, alert_type=alert_type)
    session.add(alert)
    await session.flush()
    return alert


async def get_unread_count(session: AsyncSession) -> int:
    """Return count of unread alerts."""
    stmt = select(func.count()).select_from(Alert).where(Alert.is_read == False)  # noqa: E712
    result = await session.execute(stmt)
    return result.scalar_one()


async def list_alerts(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> list[Alert]:
    """Return alerts ordered by created_at desc with joined load on relationships."""
    stmt = (
        select(Alert)
        .options(joinedload(Alert.scrape_result), joinedload(Alert.watch_query))
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def mark_alert_read(session: AsyncSession, alert_id: int) -> Alert | None:
    """Set is_read=True for an alert. Returns alert or None if not found."""
    stmt = select(Alert).where(Alert.id == alert_id)
    result = await session.execute(stmt)
    alert = result.scalar_one_or_none()
    if alert is None:
        return None
    alert.is_read = True
    await session.flush()
    return alert


async def dismiss_all_alerts(session: AsyncSession) -> int:
    """Bulk update all unread alerts to is_read=True. Returns count updated."""
    stmt = (
        update(Alert)
        .where(Alert.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    result = await session.execute(stmt)
    await session.flush()
    return result.rowcount


async def is_within_cooldown(
    session: AsyncSession, watch_query_id: int, cooldown_hours: int
) -> bool:
    """Check if the most recent alert for this watch query is within the cooldown window."""
    stmt = select(func.max(Alert.created_at)).where(Alert.watch_query_id == watch_query_id)
    result = await session.execute(stmt)
    last_alert_at = result.scalar_one_or_none()
    if last_alert_at is None:
        return False
    cutoff = datetime.utcnow() - timedelta(hours=cooldown_hours)
    return last_alert_at >= cutoff
