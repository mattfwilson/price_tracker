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
