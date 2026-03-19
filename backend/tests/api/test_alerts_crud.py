"""Tests for alert CRUD API endpoints."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.models.alert import Alert
from app.models.base import Base
from app.models.retailer_url import RetailerUrl
from app.models.scrape_job import ScrapeJob
from app.models.scrape_result import ScrapeResult
from app.models.watch_query import WatchQuery
from main import app


@pytest_asyncio.fixture
async def client_with_db():
    """Async test client that also yields a session factory for seeding data."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, session_factory
    app.dependency_overrides.clear()
    await engine.dispose()


async def seed_alert(session_factory, **overrides):
    """Create a full chain: WatchQuery -> RetailerUrl -> ScrapeJob -> ScrapeResult -> Alert."""
    async with session_factory() as session:
        wq = WatchQuery(
            name=overrides.get("query_name", "Test Query"),
            threshold_cents=overrides.get("threshold_cents", 2000),
        )
        session.add(wq)
        await session.flush()

        ru = RetailerUrl(
            watch_query_id=wq.id,
            url=overrides.get("url", "https://example.com/product"),
        )
        session.add(ru)
        await session.flush()

        sj = ScrapeJob(watch_query_id=wq.id, status="completed")
        session.add(sj)
        await session.flush()

        sr = ScrapeResult(
            retailer_url_id=ru.id,
            scrape_job_id=sj.id,
            product_name=overrides.get("product_name", "Test Product"),
            price_cents=overrides.get("price_cents", 1999),
            listing_url=overrides.get("listing_url", "https://example.com/product"),
            retailer_name=overrides.get("retailer_name", "TestRetailer"),
        )
        session.add(sr)
        await session.flush()

        alert = Alert(
            scrape_result_id=sr.id,
            watch_query_id=wq.id,
            is_read=overrides.get("is_read", False),
        )
        session.add(alert)
        await session.flush()

        await session.commit()
        return {
            "alert_id": alert.id,
            "watch_query_id": wq.id,
            "scrape_result_id": sr.id,
        }


@pytest.mark.asyncio
async def test_list_alerts_empty(client_with_db):
    client, _ = client_with_db
    response = await client.get("/alerts/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_alerts_with_data(client_with_db):
    client, session_factory = client_with_db
    await seed_alert(
        session_factory,
        query_name="My Watch",
        product_name="Widget",
        price_cents=1500,
        retailer_name="Amazon",
        listing_url="https://amazon.com/widget",
    )

    response = await client.get("/alerts/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    alert = data[0]
    assert alert["watch_query_name"] == "My Watch"
    assert alert["product_name"] == "Widget"
    assert alert["price_cents"] == 1500
    assert alert["retailer_name"] == "Amazon"
    assert alert["listing_url"] == "https://amazon.com/widget"
    assert alert["is_read"] is False
    assert "created_at" in alert


@pytest.mark.asyncio
async def test_list_alerts_pagination(client_with_db):
    client, session_factory = client_with_db
    await seed_alert(session_factory, query_name="First")
    await seed_alert(session_factory, query_name="Second")
    await seed_alert(session_factory, query_name="Third")

    response = await client.get("/alerts/?limit=1&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_list_alerts_ordered_newest_first(client_with_db):
    client, session_factory = client_with_db
    await seed_alert(session_factory, query_name="Older")
    await seed_alert(session_factory, query_name="Newer")

    response = await client.get("/alerts/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Newest first (higher ID = newer in test with SQLite second-precision)
    assert data[0]["id"] > data[1]["id"]


@pytest.mark.asyncio
async def test_mark_alert_read(client_with_db):
    client, session_factory = client_with_db
    ids = await seed_alert(session_factory)

    response = await client.patch(f"/alerts/{ids['alert_id']}/read")
    assert response.status_code == 200
    data = response.json()
    assert data["is_read"] is True
    assert data["id"] == ids["alert_id"]


@pytest.mark.asyncio
async def test_mark_alert_read_not_found(client_with_db):
    client, _ = client_with_db
    response = await client.patch("/alerts/999/read")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dismiss_all(client_with_db):
    client, session_factory = client_with_db
    await seed_alert(session_factory)
    await seed_alert(session_factory)

    response = await client.post("/alerts/dismiss-all")
    assert response.status_code == 200
    data = response.json()
    assert data["dismissed_count"] == 2


@pytest.mark.asyncio
async def test_dismiss_all_when_none(client_with_db):
    client, session_factory = client_with_db
    await seed_alert(session_factory, is_read=True)

    response = await client.post("/alerts/dismiss-all")
    assert response.status_code == 200
    data = response.json()
    assert data["dismissed_count"] == 0


@pytest.mark.asyncio
async def test_unread_count(client_with_db):
    client, session_factory = client_with_db
    await seed_alert(session_factory, is_read=False)
    await seed_alert(session_factory, is_read=False)
    await seed_alert(session_factory, is_read=True)

    response = await client.get("/alerts/unread-count")
    assert response.status_code == 200
    data = response.json()
    assert data["unread_count"] == 2


@pytest.mark.asyncio
async def test_unread_count_after_read(client_with_db):
    client, session_factory = client_with_db
    ids = await seed_alert(session_factory, is_read=False)
    await seed_alert(session_factory, is_read=False)

    # Verify initial unread count
    response = await client.get("/alerts/unread-count")
    assert response.json()["unread_count"] == 2

    # Mark one as read
    await client.patch(f"/alerts/{ids['alert_id']}/read")

    # Verify unread count decremented
    response = await client.get("/alerts/unread-count")
    assert response.json()["unread_count"] == 1
