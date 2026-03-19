"""Tests for scrape and price history API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.scrapers.base import ScrapeData


@pytest.fixture
def mock_scrape_data():
    """Return a ScrapeData that scrape_single_url would produce."""
    return ScrapeData(
        product_name="Test Product",
        price_cents=1999,
        listing_url="https://example.com/product/123",
        retailer_name="Example",
    )


@pytest.mark.asyncio
async def test_trigger_scrape(client: AsyncClient, mock_scrape_data: ScrapeData):
    # Create a watch query first
    create_resp = await client.post(
        "/watch-queries/",
        json={
            "name": "Scrape Test",
            "threshold_cents": 2500,
            "urls": ["https://example.com/product"],
        },
    )
    assert create_resp.status_code == 201
    query_id = create_resp.json()["id"]

    # Trigger scrape with mocked browser interaction
    with patch(
        "app.services.scrape_service.scrape_single_url",
        new_callable=AsyncMock,
        return_value=mock_scrape_data,
    ):
        response = await client.post(f"/watch-queries/{query_id}/scrape")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] is not None
    assert data["status"] == "success"
    assert isinstance(data["results"], list)
    assert len(data["results"]) == 1

    result = data["results"][0]
    assert result["product_name"] == "Test Product"
    assert result["price_cents"] == 1999
    assert result["retailer_name"] == "Example"
    assert result["direction"] == "new"
    assert result["delta_cents"] == 0


@pytest.mark.asyncio
async def test_trigger_scrape_404(client: AsyncClient):
    response = await client.post("/watch-queries/99999/scrape")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_history(client: AsyncClient, mock_scrape_data: ScrapeData):
    # Create a watch query and get the retailer_url id
    create_resp = await client.post(
        "/watch-queries/",
        json={
            "name": "History Test",
            "threshold_cents": 3000,
            "urls": ["https://example.com/product"],
        },
    )
    assert create_resp.status_code == 201
    query_id = create_resp.json()["id"]
    retailer_url_id = create_resp.json()["retailer_urls"][0]["id"]

    # First scrape at $19.99
    with patch(
        "app.services.scrape_service.scrape_single_url",
        new_callable=AsyncMock,
        return_value=mock_scrape_data,
    ):
        resp1 = await client.post(f"/watch-queries/{query_id}/scrape")
    assert resp1.status_code == 200

    # Second scrape at $17.99 (price drop)
    drop_data = ScrapeData(
        product_name="Test Product",
        price_cents=1799,
        listing_url="https://example.com/product/123",
        retailer_name="Example",
    )
    with patch(
        "app.services.scrape_service.scrape_single_url",
        new_callable=AsyncMock,
        return_value=drop_data,
    ):
        resp2 = await client.post(f"/watch-queries/{query_id}/scrape")
    assert resp2.status_code == 200

    # Fetch history
    response = await client.get(f"/retailer-urls/{retailer_url_id}/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 2

    # First record (newest) -- price drop from 1999 to 1799
    assert history[0]["price_cents"] == 1799
    assert history[0]["direction"] == "lower"
    assert history[0]["delta_cents"] == -200

    # Second record (oldest) -- first ever scrape
    assert history[1]["direction"] == "new"


@pytest.mark.asyncio
async def test_get_history_empty(client: AsyncClient):
    response = await client.get("/retailer-urls/99999/history")
    assert response.status_code == 200
    assert response.json() == []
