"""Tests for SSE alert streaming endpoint."""

import asyncio

import pytest

from app.services.alert_service import (
    _sse_clients,
    add_sse_client,
    broadcast_alert,
    remove_sse_client,
)


@pytest.mark.asyncio
async def test_sse_stream_connects(client):
    """GET /alerts/stream returns 200 with content-type text/event-stream."""
    async with client.stream("GET", "/alerts/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        # Don't consume the whole stream, just verify connection
        async for _line in response.aiter_lines():
            break


@pytest.mark.asyncio
async def test_sse_stream_receives_broadcast(client):
    """Connect SSE, broadcast an alert, verify event arrives with correct fields."""
    event_data = {
        "alert_id": 1,
        "watch_query_id": 1,
        "watch_query_name": "Test Query",
        "product_name": "Test Product",
        "price_cents": 999,
        "retailer_name": "Amazon",
        "listing_url": "https://amazon.com/test",
        "created_at": "2026-03-18T00:00:00",
        "unread_count": 5,
    }

    received_lines: list[str] = []

    async def read_stream():
        async with client.stream("GET", "/alerts/stream") as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                received_lines.append(line)
                if "alert_id" in line:
                    break

    task = asyncio.create_task(read_stream())
    # Give connection time to establish and register the queue
    await asyncio.sleep(0.2)

    await broadcast_alert(event_data)

    try:
        await asyncio.wait_for(task, timeout=5.0)
    except asyncio.TimeoutError:
        task.cancel()

    data_lines = [l for l in received_lines if l.startswith("data:")]
    assert len(data_lines) >= 1
    assert "alert_id" in data_lines[0]
    assert "Test Product" in data_lines[0]
    assert "unread_count" in data_lines[0]


@pytest.mark.asyncio
async def test_sse_client_cleanup():
    """After disconnect, client queue is removed from _sse_clients set."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    initial_count = len(_sse_clients)

    add_sse_client(queue)
    assert queue in _sse_clients
    assert len(_sse_clients) == initial_count + 1

    remove_sse_client(queue)
    assert queue not in _sse_clients
    assert len(_sse_clients) == initial_count
