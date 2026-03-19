"""Tests for Alembic migration correctness and integer cents enforcement."""

import os
import sqlite3

import pytest
from sqlalchemy import Integer

from app.models import WatchQuery, ScrapeResult


@pytest.fixture
def migrated_db(tmp_path, monkeypatch):
    """Run alembic upgrade head against a temporary SQLite database."""
    from pathlib import Path
    from alembic.config import Config
    from alembic import command
    from app.core.config import settings

    db_path = tmp_path / "test_migrations.db"

    # Patch the already-instantiated settings singleton so env.py picks up the temp path
    monkeypatch.setattr(settings, "database_path", Path(str(db_path)))

    alembic_cfg = Config(
        os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    )
    command.upgrade(alembic_cfg, "head")

    yield db_path


def test_migration_creates_all_tables(migrated_db):
    """Alembic upgrade head must create exactly 6 non-alembic tables."""
    conn = sqlite3.connect(str(migrated_db))
    tables = sorted(
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'alembic%'"
        ).fetchall()
    )
    conn.close()
    expected = sorted([
        "alerts",
        "app_settings",
        "retailer_urls",
        "scrape_jobs",
        "scrape_results",
        "watch_queries",
    ])
    assert tables == expected, f"Expected {expected}, got {tables}"


def test_migration_seeds_app_settings(migrated_db):
    """Migration must seed app_settings with id=1 and default_schedule='daily'."""
    conn = sqlite3.connect(str(migrated_db))
    row = conn.execute(
        "SELECT id, default_schedule FROM app_settings WHERE id=1"
    ).fetchone()
    conn.close()
    assert row is not None, "app_settings default row not seeded"
    assert row[0] == 1
    assert row[1] == "daily"


def test_price_columns_are_integer():
    """Price columns must use Integer type (not Float or Numeric) for cents storage."""
    wq_cols = {c.name: c.type for c in WatchQuery.__table__.columns}
    assert isinstance(
        wq_cols["threshold_cents"], Integer
    ), f"threshold_cents is {type(wq_cols['threshold_cents'])}, expected Integer"

    sr_cols = {c.name: c.type for c in ScrapeResult.__table__.columns}
    assert isinstance(
        sr_cols["price_cents"], Integer
    ), f"price_cents is {type(sr_cols['price_cents'])}, expected Integer"


def test_all_tables_have_expected_columns(migrated_db):
    """Key columns must exist in watch_queries and scrape_results tables."""
    conn = sqlite3.connect(str(migrated_db))

    wq_cols = [r[1] for r in conn.execute("PRAGMA table_info(watch_queries)").fetchall()]
    for col in ("id", "name", "threshold_cents", "is_active", "schedule"):
        assert col in wq_cols, f"watch_queries missing column: {col}"

    sr_cols = [r[1] for r in conn.execute("PRAGMA table_info(scrape_results)").fetchall()]
    for col in ("id", "price_cents", "product_name", "listing_url"):
        assert col in sr_cols, f"scrape_results missing column: {col}"

    conn.close()
