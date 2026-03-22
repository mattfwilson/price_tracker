"""Tests for watch query API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_watch_query(client: AsyncClient):
    response = await client.post(
        "/watch-queries/",
        json={
            "name": "Test Query",
            "threshold_cents": 1999,
            "urls": ["https://example.com/product"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Test Query"
    assert data["threshold_cents"] == 1999
    assert isinstance(data["retailer_urls"], list)
    assert len(data["retailer_urls"]) == 1
    assert data["retailer_urls"][0]["url"] == "https://example.com/product"


@pytest.mark.asyncio
async def test_create_watch_query_dedup_urls(client: AsyncClient):
    response = await client.post(
        "/watch-queries/",
        json={
            "name": "Dedup Test",
            "threshold_cents": 500,
            "urls": ["https://a.com", "https://b.com", "https://a.com"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["retailer_urls"]) == 2


@pytest.mark.asyncio
async def test_create_watch_query_empty_name_422(client: AsyncClient):
    response = await client.post(
        "/watch-queries/",
        json={
            "name": "",
            "threshold_cents": 500,
            "urls": ["https://a.com"],
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_watch_query_no_urls_422(client: AsyncClient):
    response = await client.post(
        "/watch-queries/",
        json={
            "name": "No URLs",
            "threshold_cents": 500,
            "urls": [],
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_watch_queries(client: AsyncClient):
    # Create 2 queries
    await client.post(
        "/watch-queries/",
        json={"name": "First Query", "threshold_cents": 1000, "urls": ["https://a.com"]},
    )
    await client.post(
        "/watch-queries/",
        json={"name": "Second Query", "threshold_cents": 2000, "urls": ["https://b.com"]},
    )

    response = await client.get("/watch-queries/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Ordered by created_at desc -- newest first
    assert data[0]["name"] == "Second Query"


@pytest.mark.asyncio
async def test_get_watch_query(client: AsyncClient):
    # Create a query
    create_resp = await client.post(
        "/watch-queries/",
        json={"name": "Detail Query", "threshold_cents": 1500, "urls": ["https://c.com"]},
    )
    query_id = create_resp.json()["id"]

    response = await client.get(f"/watch-queries/{query_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == query_id
    assert data["name"] == "Detail Query"
    assert data["threshold_cents"] == 1500
    assert data["is_active"] is True
    assert data["schedule"] == "daily"
    assert isinstance(data["retailer_urls"], list)
    assert len(data["retailer_urls"]) == 1
    # No scrapes yet, so latest_result should be None
    assert data["retailer_urls"][0]["latest_result"] is None


@pytest.mark.asyncio
async def test_get_watch_query_404(client: AsyncClient):
    response = await client.get("/watch-queries/99999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_watch_query(client: AsyncClient):
    # Create a query
    create_resp = await client.post(
        "/watch-queries/",
        json={"name": "Original Name", "threshold_cents": 1000, "urls": ["https://d.com"]},
    )
    query_id = create_resp.json()["id"]
    original_url_count = len(create_resp.json()["retailer_urls"])

    response = await client.patch(
        f"/watch-queries/{query_id}",
        json={"name": "Updated Name", "threshold_cents": 2999},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["threshold_cents"] == 2999
    # Original URLs preserved
    assert len(data["retailer_urls"]) == original_url_count


@pytest.mark.asyncio
async def test_update_watch_query_urls_with_dedup(client: AsyncClient):
    # Create a query with one URL
    create_resp = await client.post(
        "/watch-queries/",
        json={"name": "URL Test", "threshold_cents": 500, "urls": ["https://a.com"]},
    )
    query_id = create_resp.json()["id"]

    # Replace URLs with dedup
    response = await client.patch(
        f"/watch-queries/{query_id}",
        json={"urls": ["https://b.com", "https://c.com", "https://b.com"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["retailer_urls"]) == 2
    returned_urls = sorted([u["url"] for u in data["retailer_urls"]])
    assert returned_urls == ["https://b.com", "https://c.com"]


@pytest.mark.asyncio
async def test_delete_watch_query(client: AsyncClient):
    # Create a query
    create_resp = await client.post(
        "/watch-queries/",
        json={"name": "To Delete", "threshold_cents": 100, "urls": ["https://e.com"]},
    )
    query_id = create_resp.json()["id"]

    response = await client.delete(f"/watch-queries/{query_id}")
    assert response.status_code == 204

    # Verify it's gone
    get_resp = await client.get(f"/watch-queries/{query_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_watch_query_404(client: AsyncClient):
    response = await client.delete("/watch-queries/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_with_pct_drop_fields(client: AsyncClient):
    """POST /watch-queries with pct_drop_threshold and alert_cooldown_hours returns those fields."""
    response = await client.post(
        "/watch-queries/",
        json={
            "name": "PCT Drop Test",
            "threshold_cents": 2000,
            "urls": ["https://example.com/product"],
            "pct_drop_threshold": 10.0,
            "alert_cooldown_hours": 12,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["pct_drop_threshold"] == 10.0
    assert data["alert_cooldown_hours"] == 12


@pytest.mark.asyncio
async def test_update_pct_drop_threshold(client: AsyncClient):
    """PATCH /watch-queries/{id} with pct_drop_threshold updates the field."""
    create_resp = await client.post(
        "/watch-queries/",
        json={
            "name": "Update PCT",
            "threshold_cents": 1000,
            "urls": ["https://example.com/p"],
        },
    )
    query_id = create_resp.json()["id"]

    response = await client.patch(
        f"/watch-queries/{query_id}",
        json={"pct_drop_threshold": 15.0},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pct_drop_threshold"] == 15.0


@pytest.mark.asyncio
async def test_list_includes_new_fields(client: AsyncClient):
    """GET /watch-queries returns pct_drop_threshold and alert_cooldown_hours."""
    await client.post(
        "/watch-queries/",
        json={
            "name": "List Fields Test",
            "threshold_cents": 500,
            "urls": ["https://example.com/x"],
            "pct_drop_threshold": 10.0,
            "alert_cooldown_hours": 6,
        },
    )

    response = await client.get("/watch-queries/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    item = data[0]
    assert "pct_drop_threshold" in item
    assert item["pct_drop_threshold"] == 10.0
    assert "alert_cooldown_hours" in item
    assert item["alert_cooldown_hours"] == 6


@pytest.mark.asyncio
async def test_detail_all_time_low_true(client: AsyncClient):
    """GET /watch-queries/{id} returns is_all_time_low=true when current is the lowest."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.core.database import get_db
    from app.models.base import Base
    from app.models.retailer_url import RetailerUrl
    from app.models.scrape_job import ScrapeJob
    from app.models.scrape_result import ScrapeResult
    from main import app as fastapi_app

    # We need direct DB access; create a fresh isolated setup
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = override_get_db
    from httpx import ASGITransport, AsyncClient as HC
    transport = ASGITransport(app=fastapi_app)
    async with HC(transport=transport, base_url="http://test") as test_client:
        # Create watch query via API
        create_resp = await test_client.post(
            "/watch-queries/",
            json={"name": "ATL True", "threshold_cents": 1000, "urls": ["https://example.com/atl"]},
        )
        query_id = create_resp.json()["id"]
        url_id = create_resp.json()["retailer_urls"][0]["id"]

        # Seed a scrape result directly
        async with session_factory() as session:
            sj = ScrapeJob(watch_query_id=query_id, status="completed")
            session.add(sj)
            await session.flush()
            sr = ScrapeResult(
                retailer_url_id=url_id,
                scrape_job_id=sj.id,
                product_name="ATL Product",
                price_cents=500,
                listing_url="https://example.com/atl",
                retailer_name="TestStore",
            )
            session.add(sr)
            await session.commit()

        # GET detail
        response = await test_client.get(f"/watch-queries/{query_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_all_time_low"] is True

    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_detail_all_time_low_false(client: AsyncClient):
    """GET /watch-queries/{id} returns is_all_time_low=false when a lower historical price exists."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.core.database import get_db
    from app.models.base import Base
    from app.models.retailer_url import RetailerUrl
    from app.models.scrape_job import ScrapeJob
    from app.models.scrape_result import ScrapeResult
    from main import app as fastapi_app

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = override_get_db
    from httpx import ASGITransport, AsyncClient as HC
    transport = ASGITransport(app=fastapi_app)
    async with HC(transport=transport, base_url="http://test") as test_client:
        # Create watch query via API
        create_resp = await test_client.post(
            "/watch-queries/",
            json={"name": "ATL False", "threshold_cents": 1000, "urls": ["https://example.com/atlf"]},
        )
        query_id = create_resp.json()["id"]
        url_id = create_resp.json()["retailer_urls"][0]["id"]

        # Seed two scrape results: older at 400 (lower), current at 500
        async with session_factory() as session:
            sj = ScrapeJob(watch_query_id=query_id, status="completed")
            session.add(sj)
            await session.flush()
            # Older result - lower price
            sr1 = ScrapeResult(
                retailer_url_id=url_id,
                scrape_job_id=sj.id,
                product_name="ATL Product",
                price_cents=400,
                listing_url="https://example.com/atlf",
                retailer_name="TestStore",
            )
            session.add(sr1)
            await session.flush()
            # Current result - higher price
            sr2 = ScrapeResult(
                retailer_url_id=url_id,
                scrape_job_id=sj.id,
                product_name="ATL Product",
                price_cents=500,
                listing_url="https://example.com/atlf",
                retailer_name="TestStore",
            )
            session.add(sr2)
            await session.commit()

        # GET detail
        response = await test_client.get(f"/watch-queries/{query_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_all_time_low"] is False

    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_pause_resume_watch_query(client: AsyncClient):
    # Create a query (is_active defaults to True)
    create_resp = await client.post(
        "/watch-queries/",
        json={"name": "Pause Test", "threshold_cents": 800, "urls": ["https://f.com"]},
    )
    query_id = create_resp.json()["id"]

    # Pause
    response = await client.patch(
        f"/watch-queries/{query_id}",
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Resume
    response = await client.patch(
        f"/watch-queries/{query_id}",
        json={"is_active": True},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True
