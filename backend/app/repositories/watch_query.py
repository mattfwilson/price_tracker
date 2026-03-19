"""CRUD operations for watch queries and their retailer URLs."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.retailer_url import RetailerUrl
from app.models.watch_query import WatchQuery


async def create_watch_query(
    db: AsyncSession,
    name: str,
    threshold_cents: int,
    urls: list[str],
) -> WatchQuery:
    """Create a watch query with associated retailer URLs."""
    query = WatchQuery(
        name=name,
        threshold_cents=threshold_cents,
        retailer_urls=[RetailerUrl(url=u) for u in urls],
    )
    db.add(query)
    await db.flush()
    return query


async def get_watch_query(
    db: AsyncSession, query_id: int
) -> WatchQuery | None:
    """Get a single watch query by ID with eagerly loaded retailer URLs."""
    stmt = (
        select(WatchQuery)
        .options(selectinload(WatchQuery.retailer_urls))
        .where(WatchQuery.id == query_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_watch_queries(db: AsyncSession) -> list[WatchQuery]:
    """List all watch queries with retailer URLs, ordered by created_at desc."""
    stmt = (
        select(WatchQuery)
        .options(selectinload(WatchQuery.retailer_urls))
        .order_by(WatchQuery.created_at.desc(), WatchQuery.id.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_watch_query(
    db: AsyncSession, query_id: int, **kwargs
) -> WatchQuery | None:
    """Update a watch query's fields. Supported: name, threshold_cents, is_active, schedule."""
    query = await get_watch_query(db, query_id)
    if query is None:
        return None

    allowed_fields = {"name", "threshold_cents", "is_active", "schedule"}
    for key, value in kwargs.items():
        if key in allowed_fields and value is not None:
            setattr(query, key, value)

    await db.flush()
    return query


async def delete_watch_query(db: AsyncSession, query_id: int) -> bool:
    """Delete a watch query and cascade-delete its retailer URLs."""
    query = await get_watch_query(db, query_id)
    if query is None:
        return False

    await db.delete(query)
    await db.flush()
    return True
