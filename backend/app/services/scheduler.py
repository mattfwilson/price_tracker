"""APScheduler singleton with job registration and scheduled scrape execution."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

SCHEDULE_MAP: dict[str, dict] = {
    "every_1h": {"hours": 1},
    "every_3h": {"hours": 3},
    "every_6h": {"hours": 6},
    "every_12h": {"hours": 12},
    "daily": {"days": 1},
    "weekly": {"weeks": 1},
}


async def register_jobs_from_db() -> None:
    """Register scheduler jobs for all active watch queries in the database."""
    from app.core.database import async_session_factory
    from app.models.watch_query import WatchQuery

    async with async_session_factory() as session:
        stmt = select(WatchQuery).where(WatchQuery.is_active == True)  # noqa: E712
        result = await session.execute(stmt)
        queries = list(result.scalars().all())

    for query in queries:
        add_scrape_job(query.id, query.schedule)
        logger.info("Registered scrape job for watch query %d (%s)", query.id, query.schedule)


def add_scrape_job(watch_query_id: int, schedule: str) -> None:
    """Add or replace a scrape job for a watch query."""
    job_id = f"scrape_query_{watch_query_id}"
    interval_kwargs = SCHEDULE_MAP.get(schedule, {"days": 1})

    # Remove existing job if present
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        scheduled_scrape,
        trigger="interval",
        id=job_id,
        kwargs={"watch_query_id": watch_query_id},
        misfire_grace_time=60,
        replace_existing=True,
        **interval_kwargs,
    )


def remove_scrape_job(watch_query_id: int) -> None:
    """Remove the scrape job for a watch query, if it exists."""
    job_id = f"scrape_query_{watch_query_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


async def scheduled_scrape(watch_query_id: int) -> None:
    """Execute a scheduled scrape and evaluate alerts."""
    # Lazy imports to avoid circular imports
    from app.api.scrapes import get_browser_manager
    from app.core.database import async_session_factory
    from app.services.alert_service import evaluate_alerts_for_job
    from app.services.scrape_service import run_scrape_job

    bm = await get_browser_manager()
    async with async_session_factory() as session:
        try:
            job = await run_scrape_job(session, watch_query_id, bm)
            await evaluate_alerts_for_job(session, watch_query_id, job.id)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Scheduled scrape failed for watch query %d", watch_query_id)
            raise
