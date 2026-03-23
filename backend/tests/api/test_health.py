"""Tests for the scrape health API endpoints."""

from datetime import datetime, timedelta

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.models.base import Base
from app.models.retailer_url import RetailerUrl
from app.models.scrape_url_attempt import ScrapeUrlAttempt
from app.models.watch_query import WatchQuery
from main import app


@pytest_asyncio.fixture
async def health_client():
    """Async test client + session factory for health endpoint tests."""
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


async def _seed_url_with_attempts(
    session_factory, n_success: int, n_fail: int, name: str = "Health API Test",
    url: str = "https://walmart.com/ip/test",
) -> tuple[int, int]:
    """Helper: create a WatchQuery + RetailerUrl + attempts. Returns (wq_id, ru_id)."""
    async with session_factory() as session:
        wq = WatchQuery(name=name, threshold_cents=5000, is_active=True, schedule="daily")
        session.add(wq)
        await session.flush()
        ru = RetailerUrl(watch_query_id=wq.id, url=url)
        session.add(ru)
        await session.flush()

        now = datetime.utcnow()
        for i in range(n_success):
            session.add(ScrapeUrlAttempt(
                retailer_url_id=ru.id,
                is_success=True,
                scraped_at=now + timedelta(seconds=i),
            ))
        for j in range(n_fail):
            session.add(ScrapeUrlAttempt(
                retailer_url_id=ru.id,
                is_success=False,
                error_type="NETWORK_ERROR",
                scraped_at=now + timedelta(seconds=n_success + j),
            ))
        await session.commit()
        return wq.id, ru.id


async def test_get_health_urls_empty(health_client):
    """Empty database returns {"urls": []}."""
    client, _ = health_client
    resp = await client.get("/scrape-health/urls")
    assert resp.status_code == 200
    data = resp.json()
    assert "urls" in data
    assert data["urls"] == []


async def test_get_health_urls_structure(health_client):
    """Response contains expected fields for each URL."""
    client, session_factory = health_client
    await _seed_url_with_attempts(session_factory, n_success=8, n_fail=2)

    resp = await client.get("/scrape-health/urls")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["urls"]) == 1
    url_obj = data["urls"][0]

    expected_keys = {
        "retailer_url_id", "url", "domain", "watch_query_id",
        "watch_query_name", "status", "success_count", "window_size",
        "last_success_at", "consecutive_failures", "last_error_type",
    }
    assert expected_keys.issubset(set(url_obj.keys()))


async def test_get_health_urls_status_values(health_client):
    """Status field is one of healthy/degraded/failing, 10 successes = healthy."""
    client, session_factory = health_client
    await _seed_url_with_attempts(session_factory, n_success=10, n_fail=0)

    resp = await client.get("/scrape-health/urls")
    assert resp.status_code == 200
    url_obj = resp.json()["urls"][0]
    assert url_obj["status"] in ("healthy", "degraded", "failing")
    assert url_obj["status"] == "healthy"


async def test_existing_health_check_unaffected(health_client):
    """GET /health still returns {"status": "ok"} -- no collision with new router."""
    client, _ = health_client
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_get_health_query_filter(health_client):
    """GET /scrape-health/query/{watch_query_id} filters to a single query's URLs."""
    client, session_factory = health_client
    wq_id, ru_id = await _seed_url_with_attempts(
        session_factory, n_success=5, n_fail=5, name="Query One",
        url="https://walmart.com/ip/item1",
    )
    # Create a second watch query + URL to ensure filtering works
    await _seed_url_with_attempts(
        session_factory, n_success=3, n_fail=0, name="Query Two",
        url="https://bestbuy.com/site/item2",
    )

    resp = await client.get(f"/scrape-health/query/{wq_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "urls" in data
    assert all(u["watch_query_id"] == wq_id for u in data["urls"])
    assert len(data["urls"]) == 1
    assert data["urls"][0]["retailer_url_id"] == ru_id
