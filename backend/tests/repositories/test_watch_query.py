"""Tests for watch query repository CRUD operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.watch_query import (
    create_watch_query,
    delete_watch_query,
    get_watch_query,
    list_watch_queries,
    update_watch_query,
)


async def test_create_watch_query(db_session: AsyncSession):
    """Create a watch query with retailer URLs in a single call."""
    result = await create_watch_query(
        db_session,
        name="Test",
        threshold_cents=1999,
        urls=["https://a.com", "https://b.com"],
    )

    assert result.id is not None
    assert result.name == "Test"
    assert result.threshold_cents == 1999
    assert len(result.retailer_urls) == 2
    assert result.retailer_urls[0].url == "https://a.com"
    assert result.retailer_urls[1].url == "https://b.com"


async def test_get_watch_query(db_session: AsyncSession):
    """After creation, get_watch_query returns WatchQuery with eagerly loaded retailer_urls."""
    created = await create_watch_query(
        db_session,
        name="Fetch Test",
        threshold_cents=500,
        urls=["https://example.com"],
    )

    result = await get_watch_query(db_session, created.id)

    assert result is not None
    assert result.id == created.id
    assert result.name == "Fetch Test"
    # Eagerly loaded -- no MissingGreenlet
    assert len(result.retailer_urls) == 1
    assert result.retailer_urls[0].url == "https://example.com"


async def test_get_watch_query_not_found(db_session: AsyncSession):
    """get_watch_query returns None for non-existent ID."""
    result = await get_watch_query(db_session, 9999)
    assert result is None


async def test_list_watch_queries(db_session: AsyncSession):
    """After creating 2 queries, list returns both ordered by created_at desc."""
    await create_watch_query(
        db_session, name="First", threshold_cents=100, urls=["https://a.com"]
    )
    await create_watch_query(
        db_session, name="Second", threshold_cents=200, urls=["https://b.com"]
    )

    results = await list_watch_queries(db_session)

    assert len(results) == 2
    # Most recent first
    assert results[0].name == "Second"
    assert results[1].name == "First"


async def test_update_watch_query(db_session: AsyncSession):
    """update_watch_query changes specified fields, preserves others."""
    created = await create_watch_query(
        db_session, name="Original", threshold_cents=1000, urls=["https://a.com"]
    )

    result = await update_watch_query(
        db_session, created.id, name="Updated", threshold_cents=999
    )

    assert result is not None
    assert result.name == "Updated"
    assert result.threshold_cents == 999
    # Preserved
    assert result.is_active is True
    assert result.schedule == "daily"


async def test_delete_watch_query(db_session: AsyncSession):
    """delete_watch_query removes query and cascade-deletes retailer_urls."""
    created = await create_watch_query(
        db_session, name="Delete Me", threshold_cents=100, urls=["https://a.com"]
    )
    query_id = created.id

    deleted = await delete_watch_query(db_session, query_id)
    assert deleted is True

    # Verify gone
    result = await get_watch_query(db_session, query_id)
    assert result is None


async def test_price_stored_as_integer_cents(db_session: AsyncSession):
    """Prices are stored as integer cents, not floats."""
    created = await create_watch_query(
        db_session, name="Price Test", threshold_cents=1999, urls=["https://a.com"]
    )

    result = await get_watch_query(db_session, created.id)

    assert result is not None
    assert isinstance(result.threshold_cents, int)
    assert result.threshold_cents == 1999
