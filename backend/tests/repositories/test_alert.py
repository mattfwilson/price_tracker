"""Tests for the alert repository."""

from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.alert import Alert
from app.models.retailer_url import RetailerUrl
from app.models.scrape_job import ScrapeJob
from app.models.scrape_result import ScrapeResult
from app.models.watch_query import WatchQuery
from app.repositories.alert import (
    create_alert,
    dismiss_all_alerts,
    get_unread_count,
    list_alerts,
    mark_alert_read,
)


@pytest_asyncio.fixture
async def watch_query(db_session):
    wq = WatchQuery(name="Alert Repo Test", threshold_cents=1000, is_active=True, schedule="daily")
    db_session.add(wq)
    await db_session.flush()
    return wq


@pytest_asyncio.fixture
async def retailer_url(db_session, watch_query):
    ru = RetailerUrl(watch_query_id=watch_query.id, url="https://example.com/product")
    db_session.add(ru)
    await db_session.flush()
    return ru


@pytest_asyncio.fixture
async def scrape_job(db_session, watch_query):
    job = ScrapeJob(
        watch_query_id=watch_query.id,
        status="success",
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    db_session.add(job)
    await db_session.flush()
    return job


@pytest_asyncio.fixture
async def scrape_result(db_session, retailer_url, scrape_job):
    sr = ScrapeResult(
        retailer_url_id=retailer_url.id,
        scrape_job_id=scrape_job.id,
        product_name="Test Product",
        price_cents=800,
        listing_url="https://example.com/product",
        retailer_name="Example",
    )
    db_session.add(sr)
    await db_session.flush()
    return sr


class TestCreateAlert:
    @pytest.mark.asyncio
    async def test_create_alert(self, db_session, scrape_result, watch_query):
        alert = await create_alert(db_session, scrape_result.id, watch_query.id)
        assert alert.id is not None
        assert alert.scrape_result_id == scrape_result.id
        assert alert.watch_query_id == watch_query.id
        assert alert.is_read is False


class TestGetUnreadCount:
    @pytest.mark.asyncio
    async def test_get_unread_count(self, db_session, scrape_result, watch_query, retailer_url, scrape_job):
        """3 alerts (2 unread, 1 read) -> returns 2."""
        # Create 3 scrape results for 3 alerts
        sr2 = ScrapeResult(
            retailer_url_id=retailer_url.id, scrape_job_id=scrape_job.id,
            product_name="P2", price_cents=700, listing_url="https://x.com/2", retailer_name="Ex",
        )
        sr3 = ScrapeResult(
            retailer_url_id=retailer_url.id, scrape_job_id=scrape_job.id,
            product_name="P3", price_cents=600, listing_url="https://x.com/3", retailer_name="Ex",
        )
        db_session.add_all([sr2, sr3])
        await db_session.flush()

        a1 = await create_alert(db_session, scrape_result.id, watch_query.id)
        a2 = await create_alert(db_session, sr2.id, watch_query.id)
        a3 = await create_alert(db_session, sr3.id, watch_query.id)

        # Mark one as read
        a3.is_read = True
        await db_session.flush()

        count = await get_unread_count(db_session)
        assert count == 2


class TestListAlerts:
    @pytest.mark.asyncio
    async def test_list_alerts(self, db_session, scrape_result, watch_query):
        await create_alert(db_session, scrape_result.id, watch_query.id)
        alerts = await list_alerts(db_session)
        assert len(alerts) == 1


class TestMarkAlertRead:
    @pytest.mark.asyncio
    async def test_mark_alert_read(self, db_session, scrape_result, watch_query):
        alert = await create_alert(db_session, scrape_result.id, watch_query.id)
        assert alert.is_read is False

        updated = await mark_alert_read(db_session, alert.id)
        assert updated is not None
        assert updated.is_read is True

    @pytest.mark.asyncio
    async def test_mark_alert_read_not_found(self, db_session):
        result = await mark_alert_read(db_session, 999)
        assert result is None


class TestDismissAllAlerts:
    @pytest.mark.asyncio
    async def test_dismiss_all_alerts(self, db_session, scrape_result, watch_query, retailer_url, scrape_job):
        sr2 = ScrapeResult(
            retailer_url_id=retailer_url.id, scrape_job_id=scrape_job.id,
            product_name="P2", price_cents=700, listing_url="https://x.com/2", retailer_name="Ex",
        )
        db_session.add(sr2)
        await db_session.flush()

        a1 = await create_alert(db_session, scrape_result.id, watch_query.id)
        a2 = await create_alert(db_session, sr2.id, watch_query.id)

        count = await dismiss_all_alerts(db_session)
        assert count == 2

        unread = await get_unread_count(db_session)
        assert unread == 0
