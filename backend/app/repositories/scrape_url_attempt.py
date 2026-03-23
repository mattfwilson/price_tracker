"""CRUD and health stat queries for ScrapeUrlAttempt."""

from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retailer_url import RetailerUrl
from app.models.scrape_url_attempt import ScrapeUrlAttempt
from app.models.watch_query import WatchQuery


async def create_scrape_url_attempt(
    session: AsyncSession,
    retailer_url_id: int,
    is_success: bool,
    error_type: str | None = None,
    error_message: str | None = None,
) -> ScrapeUrlAttempt:
    """Create a new scrape attempt record."""
    attempt = ScrapeUrlAttempt(
        retailer_url_id=retailer_url_id,
        is_success=is_success,
        error_type=error_type,
        error_message=error_message,
    )
    session.add(attempt)
    await session.flush()
    return attempt


async def get_health_stats_for_all_urls(session: AsyncSession) -> list[dict]:
    """Compute health stats for all retailer URLs that have at least one attempt.

    Uses a subquery with row_number() window function to get only the last 10
    attempts per URL. Health thresholds:
    - healthy: success_rate >= 0.8
    - degraded: success_rate >= 0.5
    - failing: success_rate < 0.5

    Returns list of dicts with keys:
    retailer_url_id, url, domain, watch_query_id, watch_query_name,
    status, success_count, window_size, last_success_at,
    consecutive_failures, last_error_type
    """
    # Subquery: rank attempts per retailer_url_id newest first, keep top 10
    ranked = (
        select(
            ScrapeUrlAttempt.id,
            ScrapeUrlAttempt.retailer_url_id,
            ScrapeUrlAttempt.scraped_at,
            ScrapeUrlAttempt.is_success,
            ScrapeUrlAttempt.error_type,
            func.row_number()
            .over(
                partition_by=ScrapeUrlAttempt.retailer_url_id,
                order_by=ScrapeUrlAttempt.scraped_at.desc(),
            )
            .label("rn"),
        )
        .subquery("ranked")
    )

    window_q = (
        select(
            ranked.c.retailer_url_id,
            func.sum(case((ranked.c.is_success, 1), else_=0)).label("success_count"),
            func.count().label("window_size"),
        )
        .where(ranked.c.rn <= 10)
        .group_by(ranked.c.retailer_url_id)
        .subquery("window_agg")
    )

    # last_success_at: MAX scraped_at over ALL attempts where is_success=True
    last_success_q = (
        select(
            ScrapeUrlAttempt.retailer_url_id,
            func.max(ScrapeUrlAttempt.scraped_at).label("last_success_at"),
        )
        .where(ScrapeUrlAttempt.is_success.is_(True))
        .group_by(ScrapeUrlAttempt.retailer_url_id)
        .subquery("last_success")
    )

    # last_error_type: error_type from most recent failed attempt
    # Use a subquery with row_number over failures
    ranked_failures = (
        select(
            ScrapeUrlAttempt.retailer_url_id,
            ScrapeUrlAttempt.error_type,
            func.row_number()
            .over(
                partition_by=ScrapeUrlAttempt.retailer_url_id,
                order_by=ScrapeUrlAttempt.scraped_at.desc(),
            )
            .label("rn"),
        )
        .where(ScrapeUrlAttempt.is_success.is_(False))
        .subquery("ranked_failures")
    )

    last_error_q = (
        select(
            ranked_failures.c.retailer_url_id,
            ranked_failures.c.error_type.label("last_error_type"),
        )
        .where(ranked_failures.c.rn == 1)
        .subquery("last_error")
    )

    # Main query joining everything
    stmt = (
        select(
            RetailerUrl.id.label("retailer_url_id"),
            RetailerUrl.url,
            RetailerUrl.watch_query_id,
            WatchQuery.name.label("watch_query_name"),
            window_q.c.success_count,
            window_q.c.window_size,
            last_success_q.c.last_success_at,
            last_error_q.c.last_error_type,
        )
        .join(window_q, window_q.c.retailer_url_id == RetailerUrl.id)
        .join(WatchQuery, WatchQuery.id == RetailerUrl.watch_query_id)
        .outerjoin(last_success_q, last_success_q.c.retailer_url_id == RetailerUrl.id)
        .outerjoin(last_error_q, last_error_q.c.retailer_url_id == RetailerUrl.id)
        .order_by(RetailerUrl.id)
    )

    result = await session.execute(stmt)
    rows = result.all()

    # Compute consecutive_failures and status in Python after the query
    # For consecutive_failures: need separate query per URL (or use ranked subquery)
    # We'll compute consecutive_failures using ranked window data in a separate query
    consec = await _compute_consecutive_failures(session)

    stats = []
    for row in rows:
        url = row.url
        hostname = urlparse(url).hostname or ""
        # Remove www. prefix for cleaner domain display
        domain = hostname.removeprefix("www.")

        success_count = int(row.success_count)
        window_size = int(row.window_size)
        success_rate = success_count / window_size if window_size > 0 else 0.0

        if success_rate >= 0.8:
            status = "healthy"
        elif success_rate >= 0.5:
            status = "degraded"
        else:
            status = "failing"

        stats.append({
            "retailer_url_id": row.retailer_url_id,
            "url": url,
            "domain": domain,
            "watch_query_id": row.watch_query_id,
            "watch_query_name": row.watch_query_name,
            "status": status,
            "success_count": success_count,
            "window_size": window_size,
            "last_success_at": row.last_success_at,
            "consecutive_failures": consec.get(row.retailer_url_id, 0),
            "last_error_type": row.last_error_type,
        })

    return stats


async def _compute_consecutive_failures(session: AsyncSession) -> dict[int, int]:
    """Compute trailing consecutive failure count per retailer_url_id.

    Looks at the last 10 attempts per URL (ordered newest first).
    Counts failures from the start until a success is found.
    If no successes in the window, consecutive = window_size.
    """
    # Get ranked attempts (last 10 per URL), ordered by rn ascending (oldest in window first)
    ranked = (
        select(
            ScrapeUrlAttempt.retailer_url_id,
            ScrapeUrlAttempt.is_success,
            func.row_number()
            .over(
                partition_by=ScrapeUrlAttempt.retailer_url_id,
                order_by=ScrapeUrlAttempt.scraped_at.desc(),
            )
            .label("rn"),
        )
        .subquery("ranked_for_consec")
    )

    stmt = (
        select(
            ranked.c.retailer_url_id,
            ranked.c.is_success,
            ranked.c.rn,
        )
        .where(ranked.c.rn <= 10)
        .order_by(ranked.c.retailer_url_id, ranked.c.rn)
    )

    result = await session.execute(stmt)
    rows = result.all()

    # Group by retailer_url_id
    by_url: dict[int, list[bool]] = {}
    for row in rows:
        by_url.setdefault(row.retailer_url_id, []).append(row.is_success)

    # Count trailing consecutive failures (rn=1 is the most recent)
    consec: dict[int, int] = {}
    for url_id, successes in by_url.items():
        # successes is ordered by rn ascending: index 0 = most recent attempt
        count = 0
        for is_success in successes:
            if not is_success:
                count += 1
            else:
                break
        consec[url_id] = count

    return consec
