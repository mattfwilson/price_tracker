"""Tests for the scheduler service."""

import pytest
import pytest_asyncio

from app.models.watch_query import WatchQuery
from app.services.scheduler import (
    SCHEDULE_MAP,
    add_scrape_job,
    register_jobs_from_db,
    remove_scrape_job,
    scheduler,
)


@pytest.fixture
def running_scheduler():
    """Start the scheduler for tests and shut it down after."""
    scheduler.start(paused=True)
    yield scheduler
    scheduler.shutdown(wait=False)


class TestScheduleMap:
    def test_schedule_map_keys(self):
        assert set(SCHEDULE_MAP.keys()) == {"every_6h", "every_12h", "daily", "weekly"}

    def test_schedule_map_values(self):
        assert SCHEDULE_MAP["every_6h"] == {"hours": 6}
        assert SCHEDULE_MAP["every_12h"] == {"hours": 12}
        assert SCHEDULE_MAP["daily"] == {"days": 1}
        assert SCHEDULE_MAP["weekly"] == {"weeks": 1}


class TestAddRemoveJobs:
    def test_add_scrape_job(self, running_scheduler):
        add_scrape_job(1, "daily")
        job = running_scheduler.get_job("scrape_query_1")
        assert job is not None

    def test_remove_scrape_job(self, running_scheduler):
        add_scrape_job(1, "daily")
        remove_scrape_job(1)
        job = running_scheduler.get_job("scrape_query_1")
        assert job is None

    def test_add_replaces_existing(self, running_scheduler):
        add_scrape_job(1, "daily")
        add_scrape_job(1, "every_6h")
        # Should still be exactly one job with that id
        job = running_scheduler.get_job("scrape_query_1")
        assert job is not None
        # No duplicate -- get_jobs should have only one with that id
        all_jobs = running_scheduler.get_jobs()
        scrape_jobs = [j for j in all_jobs if j.id == "scrape_query_1"]
        assert len(scrape_jobs) == 1

    def test_remove_nonexistent_no_error(self, running_scheduler):
        # Should not raise
        remove_scrape_job(999)


class TestRegisterJobsFromDb:
    @pytest.mark.asyncio
    async def test_register_jobs_from_db(self, db_session, running_scheduler, monkeypatch):
        """Given 2 active and 1 paused WatchQuery, register_jobs_from_db creates 2 jobs."""
        # Create test watch queries
        wq1 = WatchQuery(name="Active 1", threshold_cents=1000, is_active=True, schedule="daily")
        wq2 = WatchQuery(name="Active 2", threshold_cents=2000, is_active=True, schedule="every_6h")
        wq3 = WatchQuery(name="Paused", threshold_cents=3000, is_active=False, schedule="weekly")
        db_session.add_all([wq1, wq2, wq3])
        await db_session.flush()

        # Monkeypatch async_session_factory to return our test session
        from unittest.mock import AsyncMock, MagicMock
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_factory():
            yield db_session

        monkeypatch.setattr(
            "app.services.scheduler.async_session_factory",
            mock_session_factory,
        )

        await register_jobs_from_db()

        # Should have 2 jobs (for the 2 active queries)
        all_jobs = running_scheduler.get_jobs()
        scrape_jobs = [j for j in all_jobs if j.id.startswith("scrape_query_")]
        assert len(scrape_jobs) == 2
