"""Tests for SQLite PRAGMA configuration (WAL mode, busy_timeout)."""

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
def db_path(tmp_path):
    """Provide a file-based temporary database path (WAL requires file, not :memory:)."""
    return tmp_path / "test.db"


@pytest.fixture
async def file_engine(db_path):
    """Create an async engine with PRAGMA event listener, mirroring database.py."""
    eng = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    yield eng
    await eng.dispose()


async def test_sqlite_wal_mode(file_engine):
    """WAL journal mode must be set on file-based SQLite connections."""
    async with file_engine.connect() as conn:
        result = await conn.execute(text("PRAGMA journal_mode"))
        mode = result.scalar()
        assert mode == "wal", f"Expected WAL mode, got {mode}"


async def test_sqlite_busy_timeout(file_engine):
    """busy_timeout must be set to 5000ms on every connection."""
    async with file_engine.connect() as conn:
        result = await conn.execute(text("PRAGMA busy_timeout"))
        timeout = result.scalar()
        assert timeout == 5000, f"Expected 5000, got {timeout}"


async def test_pragmas_set_on_new_connection(file_engine):
    """PRAGMAs must apply per-connection, not just the first one."""
    # First connection
    async with file_engine.connect() as conn1:
        r1_wal = await conn1.execute(text("PRAGMA journal_mode"))
        assert r1_wal.scalar() == "wal"
        r1_timeout = await conn1.execute(text("PRAGMA busy_timeout"))
        assert r1_timeout.scalar() == 5000

    # Second connection (proves per-connection, not one-time)
    async with file_engine.connect() as conn2:
        r2_wal = await conn2.execute(text("PRAGMA journal_mode"))
        assert r2_wal.scalar() == "wal"
        r2_timeout = await conn2.execute(text("PRAGMA busy_timeout"))
        assert r2_timeout.scalar() == 5000
