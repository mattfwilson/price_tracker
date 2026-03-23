"""Tests for ScrapeUrlAttempt repository operations and health stat computation."""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.watch_query import WatchQuery
from app.models.retailer_url import RetailerUrl
from app.repositories.scrape_url_attempt import (
    create_scrape_url_attempt,
    get_health_stats_for_all_urls,
)


@pytest_asyncio.fixture
async def watch_query(db_session: AsyncSession):
    wq = WatchQuery(name="Health Test Query", threshold_cents=9999, is_active=True, schedule="daily")
    db_session.add(wq)
    await db_session.flush()
    return wq


@pytest_asyncio.fixture
async def retailer_url(db_session: AsyncSession, watch_query: WatchQuery):
    ru = RetailerUrl(watch_query_id=watch_query.id, url="https://amazon.com/dp/test123")
    db_session.add(ru)
    await db_session.flush()
    return ru


async def test_create_success_attempt(db_session: AsyncSession, retailer_url: RetailerUrl):
    """create_scrape_url_attempt with is_success=True creates row with error_type=None."""
    attempt = await create_scrape_url_attempt(
        db_session,
        retailer_url_id=retailer_url.id,
        is_success=True,
    )

    assert attempt.id is not None
    assert attempt.retailer_url_id == retailer_url.id
    assert attempt.is_success is True
    assert attempt.error_type is None
    assert attempt.error_message is None
    assert attempt.scraped_at is not None


async def test_create_failure_attempt(db_session: AsyncSession, retailer_url: RetailerUrl):
    """create_scrape_url_attempt with is_success=False and error info stores all fields."""
    attempt = await create_scrape_url_attempt(
        db_session,
        retailer_url_id=retailer_url.id,
        is_success=False,
        error_type="NETWORK_ERROR",
        error_message="timeout",
    )

    assert attempt.id is not None
    assert attempt.is_success is False
    assert attempt.error_type == "NETWORK_ERROR"
    assert attempt.error_message == "timeout"


async def _insert_attempts(db_session: AsyncSession, retailer_url_id: int, pattern: list):
    """Helper: insert attempts in order. Each item is True (success) or False (failure)."""
    now = datetime.utcnow()
    for i, success in enumerate(pattern):
        # Use explicit scraped_at offset so ordering is deterministic
        from app.models.scrape_url_attempt import ScrapeUrlAttempt
        attempt = ScrapeUrlAttempt(
            retailer_url_id=retailer_url_id,
            is_success=success,
            error_type=None if success else "NETWORK_ERROR",
            error_message=None if success else "fail",
            scraped_at=now + timedelta(seconds=i),
        )
        db_session.add(attempt)
    await db_session.flush()


async def test_health_all_success(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """10 successes -> status=healthy, success_count=10, window_size=10, consecutive_failures=0."""
    await _insert_attempts(db_session, retailer_url.id, [True] * 10)
    stats = await get_health_stats_for_all_urls(db_session)

    assert len(stats) == 1
    s = stats[0]
    assert s["retailer_url_id"] == retailer_url.id
    assert s["status"] == "healthy"
    assert s["success_count"] == 10
    assert s["window_size"] == 10
    assert s["consecutive_failures"] == 0


async def test_health_degraded(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """7 successes + 3 failures -> status=degraded, success_count=7."""
    # Most recent 3 are failures, earlier 7 are successes
    await _insert_attempts(db_session, retailer_url.id, [True] * 7 + [False] * 3)
    stats = await get_health_stats_for_all_urls(db_session)

    assert len(stats) == 1
    s = stats[0]
    assert s["status"] == "degraded"
    assert s["success_count"] == 7
    assert s["window_size"] == 10


async def test_health_failing(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """4 successes + 6 failures -> status=failing, success_count=4."""
    await _insert_attempts(db_session, retailer_url.id, [True] * 4 + [False] * 6)
    stats = await get_health_stats_for_all_urls(db_session)

    assert len(stats) == 1
    s = stats[0]
    assert s["status"] == "failing"
    assert s["success_count"] == 4
    assert s["window_size"] == 10


async def test_health_small_window(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """URL with only 3 attempts (all success) -> window_size=3, success_count=3, status=healthy."""
    await _insert_attempts(db_session, retailer_url.id, [True] * 3)
    stats = await get_health_stats_for_all_urls(db_session)

    assert len(stats) == 1
    s = stats[0]
    assert s["window_size"] == 3
    assert s["success_count"] == 3
    assert s["status"] == "healthy"


async def test_consecutive_failures_trailing(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """S,F,F,F pattern -> consecutive_failures=3 (not 3 total failures, but trailing ones)."""
    # pattern: 1 success then 3 failures (most recent)
    await _insert_attempts(db_session, retailer_url.id, [True, False, False, False])
    stats = await get_health_stats_for_all_urls(db_session)

    assert len(stats) == 1
    assert stats[0]["consecutive_failures"] == 3


async def test_consecutive_failures_not_all(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """F,F,S,F pattern (oldest to newest) -> consecutive_failures=1 (only trailing)."""
    # oldest: F, F, then S, then F (most recent)
    await _insert_attempts(db_session, retailer_url.id, [False, False, True, False])
    stats = await get_health_stats_for_all_urls(db_session)

    assert len(stats) == 1
    assert stats[0]["consecutive_failures"] == 1


async def test_last_success_at(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """last_success_at returns most recent successful attempt timestamp."""
    await _insert_attempts(db_session, retailer_url.id, [True, True, False])
    stats = await get_health_stats_for_all_urls(db_session)

    assert len(stats) == 1
    assert stats[0]["last_success_at"] is not None


async def test_last_error_type(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """last_error_type returns error_type from the most recent failed attempt."""
    await _insert_attempts(db_session, retailer_url.id, [True, False])
    stats = await get_health_stats_for_all_urls(db_session)

    assert len(stats) == 1
    assert stats[0]["last_error_type"] == "NETWORK_ERROR"


async def test_only_last_10_considered(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """Only last 10 attempts are considered even when more exist."""
    # 5 old failures + 10 recent successes = window should show 10 successes
    await _insert_attempts(db_session, retailer_url.id, [False] * 5 + [True] * 10)
    stats = await get_health_stats_for_all_urls(db_session)

    assert len(stats) == 1
    s = stats[0]
    assert s["window_size"] == 10
    assert s["success_count"] == 10
    assert s["status"] == "healthy"


async def test_empty_no_attempts(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """URL with no attempts should not appear in stats (or return with window_size=0)."""
    stats = await get_health_stats_for_all_urls(db_session)
    # URL exists but has no attempts - should not be in results
    assert len(stats) == 0


async def test_stats_include_url_and_watch_query_info(db_session: AsyncSession, retailer_url: RetailerUrl, watch_query: WatchQuery):
    """Stats include url, domain, watch_query_id, and watch_query_name."""
    await _insert_attempts(db_session, retailer_url.id, [True])
    stats = await get_health_stats_for_all_urls(db_session)

    assert len(stats) == 1
    s = stats[0]
    assert s["url"] == "https://amazon.com/dp/test123"
    assert s["domain"] == "amazon.com"
    assert s["watch_query_id"] == watch_query.id
    assert s["watch_query_name"] == "Health Test Query"
