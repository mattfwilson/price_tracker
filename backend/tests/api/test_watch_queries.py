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


# --- Stub tests for Plan 03-02 ---


@pytest.mark.skip(reason="Plan 03-02")
@pytest.mark.asyncio
async def test_list_watch_queries(client: AsyncClient):
    pass


@pytest.mark.skip(reason="Plan 03-02")
@pytest.mark.asyncio
async def test_get_watch_query(client: AsyncClient):
    pass


@pytest.mark.skip(reason="Plan 03-02")
@pytest.mark.asyncio
async def test_get_watch_query_404(client: AsyncClient):
    pass


@pytest.mark.skip(reason="Plan 03-02")
@pytest.mark.asyncio
async def test_update_watch_query(client: AsyncClient):
    pass


@pytest.mark.skip(reason="Plan 03-02")
@pytest.mark.asyncio
async def test_update_watch_query_urls_with_dedup(client: AsyncClient):
    pass


@pytest.mark.skip(reason="Plan 03-02")
@pytest.mark.asyncio
async def test_delete_watch_query(client: AsyncClient):
    pass


@pytest.mark.skip(reason="Plan 03-02")
@pytest.mark.asyncio
async def test_delete_watch_query_404(client: AsyncClient):
    pass


@pytest.mark.skip(reason="Plan 03-02")
@pytest.mark.asyncio
async def test_pause_resume_watch_query(client: AsyncClient):
    pass
