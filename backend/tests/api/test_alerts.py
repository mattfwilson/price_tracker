"""Tests for SSE alert streaming endpoint and broadcast mechanism."""

import asyncio
import json

import pytest

from app.services.alert_service import (
    _sse_clients,
    add_sse_client,
    broadcast_alert,
    remove_sse_client,
)


@pytest.mark.asyncio
async def test_sse_stream_connects():
    """GET /alerts/stream returns StreamingResponse with text/event-stream.

    ASGITransport doesn't support true SSE streaming, so we test the endpoint
    function directly.
    """
    from unittest.mock import AsyncMock

    from app.api.alerts import alert_stream

    mock_request = AsyncMock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    response = await alert_stream(mock_request)
    assert response.media_type == "text/event-stream"
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-cache"

    # Clean up the queue that was registered
    await response.body_iterator.aclose()
    for q in list(_sse_clients):
        _sse_clients.discard(q)


@pytest.mark.asyncio
async def test_sse_broadcast_delivers_to_queue():
    """Broadcast alert events arrive on registered SSE client queues with full payload."""
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

    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    add_sse_client(queue)

    try:
        await broadcast_alert(event_data)

        assert not queue.empty()
        received = queue.get_nowait()

        # Verify all required fields
        assert received["alert_id"] == 1
        assert received["watch_query_id"] == 1
        assert received["watch_query_name"] == "Test Query"
        assert received["product_name"] == "Test Product"
        assert received["price_cents"] == 999
        assert received["retailer_name"] == "Amazon"
        assert received["listing_url"] == "https://amazon.com/test"
        assert received["created_at"] == "2026-03-18T00:00:00"
        assert received["unread_count"] == 5
    finally:
        remove_sse_client(queue)


@pytest.mark.asyncio
async def test_sse_broadcast_multiple_clients():
    """Broadcast delivers to all connected clients."""
    q1: asyncio.Queue = asyncio.Queue(maxsize=50)
    q2: asyncio.Queue = asyncio.Queue(maxsize=50)
    add_sse_client(q1)
    add_sse_client(q2)

    try:
        await broadcast_alert({"alert_id": 42})
        assert not q1.empty()
        assert not q2.empty()
        assert q1.get_nowait()["alert_id"] == 42
        assert q2.get_nowait()["alert_id"] == 42
    finally:
        remove_sse_client(q1)
        remove_sse_client(q2)


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


@pytest.mark.asyncio
async def test_sse_event_generator_format():
    """Verify the SSE event generator produces correct SSE format."""
    from app.api.alerts import alert_stream

    # Test that the endpoint function exists and returns a StreamingResponse
    from unittest.mock import AsyncMock
    mock_request = AsyncMock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    response = await alert_stream(mock_request)
    assert response.media_type == "text/event-stream"
    assert response.headers.get("Cache-Control") == "no-cache"
    assert response.headers.get("X-Accel-Buffering") == "no"

    # Clean up: find and remove the queue that was added
    # The endpoint creates a queue internally, so we need to clear it
    for q in list(_sse_clients):
        # Put a message so the generator yields, then we can verify format
        q.put_nowait({
            "alert_id": 1,
            "product_name": "Test",
        })

    # Read one event from the generator
    body_parts = []
    async for chunk in response.body_iterator:
        body_parts.append(chunk)
        break  # Just get first event

    assert len(body_parts) >= 1
    event_text = body_parts[0]
    assert "event: alert" in event_text
    assert "data:" in event_text
    # Verify JSON payload in data line
    data_line = [l for l in event_text.split("\n") if l.startswith("data:")][0]
    payload = json.loads(data_line[5:])  # strip "data:" prefix
    assert payload["alert_id"] == 1

    # Cleanup: close the generator and remove any leftover queues
    await response.body_iterator.aclose()
    for q in list(_sse_clients):
        _sse_clients.discard(q)
