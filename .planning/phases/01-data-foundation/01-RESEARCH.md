# Phase 1: Data Foundation - Research

**Researched:** 2026-03-18
**Domain:** SQLAlchemy 2.0 async ORM + Alembic migrations + SQLite
**Confidence:** HIGH

## Summary

Phase 1 establishes the data layer for a Python/FastAPI price scraper: six SQLAlchemy ORM models, Alembic migration infrastructure, a repository pattern for CRUD, and hardened SQLite configuration (WAL mode, busy_timeout). The stack is mature and well-documented -- SQLAlchemy 2.0's async extension with aiosqlite is the standard approach for async FastAPI + SQLite applications.

The critical decisions are already locked: async sessions via aiosqlite, SQLAlchemy 2.0 `mapped_column()` style, Alembic auto-generate with startup migration, and a layered `backend/app/` structure. Research confirms these are all standard, well-supported patterns. The main pitfalls to watch are: SQLite batch migrations in Alembic (required for ALTER TABLE operations), PRAGMA settings being per-connection (must use event listeners), and async event listener registration requiring `sync_engine` attribute access.

**Primary recommendation:** Use Alembic's built-in `async` template (`alembic init -t async`) and enable `render_as_batch=True` in env.py from day one to avoid SQLite migration failures in later phases.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `backend/` + `frontend/` top-level split with `backend/app/` organized by layer: `models/`, `repositories/`, `services/`, `api/`, `schemas/`, `core/`
- SQLite database file at `backend/data/prices.db` (`.gitignored`)
- Alembic migrations at `backend/alembic/`, config at `backend/alembic.ini`
- `backend/main.py` is the FastAPI entry point
- Async sessions (AsyncSession + aiosqlite) with FastAPI dependency injection via `Depends(get_db)` in `backend/app/core/database.py`
- SQLAlchemy 2.0 `mapped_column()` style with `Mapped[T]` type annotations
- `app_settings` table: single-row typed columns, Phase 1 scope limited to `default_schedule` column (plus `id` PK and `updated_at`)
- Alembic auto-generate from models; migrations auto-apply on startup via `alembic upgrade head` in FastAPI lifespan

### Claude's Discretion
- Exact `core/config.py` structure (Pydantic BaseSettings vs plain dataclass)
- SQLite `busy_timeout` value (something reasonable like 5000ms)
- Whether to seed a default `app_settings` row on first run
- Test setup approach for repository layer

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.48 | Async ORM with type-safe models | Industry standard Python ORM; 2.0 adds native async + `Mapped[T]` type annotations |
| alembic | 1.18.4 | Database schema migrations | Official SQLAlchemy migration tool, same author, deep integration |
| aiosqlite | 0.22.1 | Async SQLite driver for SQLAlchemy | The only maintained async SQLite adapter; used via `sqlite+aiosqlite://` dialect |
| pydantic-settings | 2.13.1 | App configuration from env vars | FastAPI ecosystem standard for typed config; reads `.env` files automatically |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | latest | Test runner | Repository layer tests |
| pytest-asyncio | 1.3.0 | Async test support | All async repository/database tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic-settings | Plain dataclass | Dataclass is simpler but loses env var loading, `.env` file support, and validation. Use pydantic-settings -- it is the FastAPI ecosystem standard |
| Manual SQL | SQLModel | SQLModel adds another abstraction layer; pure SQLAlchemy 2.0 is more flexible and better documented for async |

**Installation:**
```bash
pip install sqlalchemy[asyncio] alembic aiosqlite pydantic-settings
pip install pytest pytest-asyncio  # dev dependencies
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── main.py                      # FastAPI entry point with lifespan
├── alembic.ini                  # Alembic config (sqlalchemy.url overridden in env.py)
├── alembic/
│   ├── env.py                   # Async engine setup, render_as_batch=True
│   ├── script.py.mako           # Migration template
│   └── versions/                # Auto-generated migration files
├── data/                        # SQLite DB lives here (.gitignored)
│   └── .gitkeep
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic BaseSettings (DB path, busy_timeout)
│   │   └── database.py          # Engine, session factory, get_db dependency
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py              # DeclarativeBase subclass
│   │   ├── watch_query.py
│   │   ├── retailer_url.py
│   │   ├── scrape_result.py
│   │   ├── scrape_job.py
│   │   ├── alert.py
│   │   └── app_settings.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── watch_query.py       # CRUD for watch_queries + retailer_urls
│   │   └── app_settings.py      # Get/update settings singleton
│   └── schemas/                 # Pydantic schemas (for later API use)
│       └── __init__.py
└── tests/
    ├── __init__.py
    ├── conftest.py              # Async DB fixtures
    └── repositories/
        ├── __init__.py
        └── test_watch_query.py
```

### Pattern 1: Async Engine + Session Factory
**What:** Centralized database connection setup with SQLite PRAGMAs applied on every connection.
**When to use:** Always -- this is the single source of database connectivity.
**Example:**
```python
# backend/app/core/database.py
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.database_path}",
    echo=settings.debug,
)

# CRITICAL: PRAGMAs must be set on the sync_engine because
# event listeners are always synchronous, even with async engines
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute(f"PRAGMA busy_timeout={settings.busy_timeout}")
    cursor.close()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    """FastAPI dependency that yields an AsyncSession."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Pattern 2: DeclarativeBase with Integer Cents
**What:** All models inherit from a shared Base; prices always stored as integer cents.
**When to use:** Every model definition.
**Example:**
```python
# backend/app/models/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )
```

```python
# backend/app/models/watch_query.py
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

class WatchQuery(Base, TimestampMixin):
    __tablename__ = "watch_queries"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    # Price threshold in integer cents (e.g., 1999 = $19.99)
    threshold_cents: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    schedule: Mapped[str] = mapped_column(String(50), default="daily")

    retailer_urls: Mapped[list["RetailerUrl"]] = relationship(
        back_populates="watch_query",
        cascade="all, delete-orphan",
    )
```

### Pattern 3: Repository Layer
**What:** Thin functions that encapsulate database queries, receiving `AsyncSession` as parameter.
**When to use:** All data access -- never put raw queries in route handlers.
**Example:**
```python
# backend/app/repositories/watch_query.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.watch_query import WatchQuery
from app.models.retailer_url import RetailerUrl

async def create_watch_query(
    db: AsyncSession,
    name: str,
    threshold_cents: int,
    urls: list[str],
) -> WatchQuery:
    query = WatchQuery(
        name=name,
        threshold_cents=threshold_cents,
        retailer_urls=[RetailerUrl(url=u) for u in urls],
    )
    db.add(query)
    await db.flush()  # Populate id without committing
    return query

async def get_watch_query(
    db: AsyncSession, query_id: int
) -> WatchQuery | None:
    stmt = (
        select(WatchQuery)
        .options(selectinload(WatchQuery.retailer_urls))
        .where(WatchQuery.id == query_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def list_watch_queries(db: AsyncSession) -> list[WatchQuery]:
    stmt = (
        select(WatchQuery)
        .options(selectinload(WatchQuery.retailer_urls))
        .order_by(WatchQuery.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
```

### Pattern 4: Alembic Async env.py with Batch Mode
**What:** Alembic env.py configured for async engine and SQLite batch migrations.
**When to use:** The `alembic/env.py` file -- set up once, rarely changed.
**Example:**
```python
# backend/alembic/env.py (key sections)
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from app.models.base import Base
from app.core.config import settings

target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(
        url=f"sqlite+aiosqlite:///{settings.database_path}",
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,  # CRITICAL for SQLite
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # CRITICAL for SQLite
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = create_async_engine(
        f"sqlite+aiosqlite:///{settings.database_path}"
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Pattern 5: FastAPI Lifespan for Startup Migration
**What:** Run `alembic upgrade head` during app startup so the DB is always current.
**When to use:** `backend/main.py` lifespan context manager.
**Example:**
```python
# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from alembic.config import Config
from alembic import command
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup
    alembic_cfg = Config(
        os.path.join(os.path.dirname(__file__), "alembic.ini")
    )
    command.upgrade(alembic_cfg, "head")
    yield

app = FastAPI(lifespan=lifespan)
```

### Anti-Patterns to Avoid
- **Lazy-loading relationships in async context:** Always use `selectinload()` or `joinedload()` -- lazy loading triggers synchronous I/O which raises `MissingGreenlet` errors in async sessions.
- **Floating-point prices:** Never use `Float` or `Numeric` for prices. Always `Integer` cents. Conversion happens at the presentation layer only.
- **Creating engine per request:** Create engine once at module level, reuse via session factory.
- **Forgetting `expire_on_commit=False`:** Without this, accessing attributes after commit raises errors in async sessions because the session cannot implicitly refresh.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema migrations | Manual `CREATE TABLE` / `ALTER TABLE` scripts | Alembic auto-generate | Migration ordering, rollback, history tracking are deceptively complex |
| SQLite ALTER TABLE | Direct column add/drop/rename | Alembic batch mode (`render_as_batch=True`) | SQLite only supports ADD COLUMN; batch mode handles the copy-and-rename dance |
| Connection pooling | Custom pool | SQLAlchemy's built-in pool | Already configured correctly for SQLite (StaticPool for in-memory, default pool otherwise) |
| Config management | Custom env parser | pydantic-settings `BaseSettings` | Handles `.env` files, type coercion, validation, defaults |
| Timestamp columns | Manual `datetime.utcnow()` in code | `server_default=func.now()` and `onupdate=func.now()` | Database-level defaults are more reliable than app-level |

**Key insight:** SQLite's migration limitations make Alembic batch mode essential, not optional. Setting `render_as_batch=True` from day one avoids discovering this limitation when Phase 3+ needs column modifications.

## Common Pitfalls

### Pitfall 1: SQLite PRAGMAs Reset Per Connection
**What goes wrong:** WAL mode and busy_timeout appear to work in dev but fail under load or after restart.
**Why it happens:** SQLite PRAGMAs are per-connection settings. `journal_mode=WAL` persists in the database file, but `busy_timeout` resets to 0 on every new connection.
**How to avoid:** Use SQLAlchemy `event.listens_for(engine.sync_engine, "connect")` to set PRAGMAs on every new connection. Note: must use `sync_engine` attribute, not the async engine directly.
**Warning signs:** Intermittent `database is locked` errors under concurrent access.

### Pitfall 2: Lazy Loading in Async Sessions
**What goes wrong:** Accessing a relationship attribute (e.g., `query.retailer_urls`) raises `MissingGreenlet` or `greenlet` errors.
**Why it happens:** Lazy loading triggers synchronous I/O which is incompatible with async sessions.
**How to avoid:** Always eager-load relationships: `selectinload(WatchQuery.retailer_urls)` in every query that accesses relationships.
**Warning signs:** `sqlalchemy.exc.MissingGreenlet` error or `greenlet_spawn has not been called`.

### Pitfall 3: Alembic autogenerate Misses Some SQLite Changes
**What goes wrong:** Running `alembic revision --autogenerate` produces an empty migration when you've changed column types or constraints.
**Why it happens:** Without `render_as_batch=True`, Alembic skips operations that SQLite doesn't natively support.
**How to avoid:** Always set `render_as_batch=True` in `context.configure()` calls in env.py.
**Warning signs:** Empty migration files after model changes.

### Pitfall 4: Forgetting expire_on_commit=False
**What goes wrong:** After `await session.commit()`, accessing model attributes raises `sqlalchemy.orm.exc.DetachedInstanceError`.
**Why it happens:** By default, SQLAlchemy expires all attributes on commit, and refreshing them requires synchronous I/O.
**How to avoid:** Set `expire_on_commit=False` in `async_sessionmaker()`.
**Warning signs:** Errors when accessing model fields after committing.

### Pitfall 5: Alembic env.py Import Path Issues
**What goes wrong:** `alembic revision --autogenerate` fails with `ModuleNotFoundError: No module named 'app'`.
**Why it happens:** Alembic runs from the directory containing `alembic.ini`, which may not have `app` on the Python path.
**How to avoid:** Add `sys.path.insert(0, os.path.dirname(__file__) + "/..")` at the top of `env.py`, or ensure the working directory is `backend/` when running alembic commands.
**Warning signs:** Import errors only when running alembic CLI (not when running the FastAPI app).

### Pitfall 6: Integer Cents Boundary
**What goes wrong:** Some code path stores a float price (e.g., 19.99) instead of integer cents (1999).
**Why it happens:** Easy to forget the conversion at one boundary, especially in tests or seed data.
**How to avoid:** Use `Integer` column type in the model so SQLAlchemy raises an error if a float is passed. Add a helper function `dollars_to_cents(amount: float) -> int` used at all ingestion boundaries.
**Warning signs:** Prices stored as 19 or 20 instead of 1999 or 2000.

## Code Examples

### Pydantic BaseSettings Configuration
```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Database
    database_path: Path = Path("data/prices.db")
    busy_timeout: int = 5000  # milliseconds
    debug: bool = False

    # App
    app_name: str = "Price Scraper"

    model_config = {
        "env_file": ".env",
        "env_prefix": "PRICE_SCRAPER_",
    }

settings = Settings()
```

### Six Table Models Summary
```python
# watch_queries: id, name, threshold_cents, is_active, schedule, created_at, updated_at
# retailer_urls: id, watch_query_id (FK), url, created_at
# scrape_results: id, retailer_url_id (FK), scrape_job_id (FK), product_name, price_cents, listing_url, created_at
# scrape_jobs: id, watch_query_id (FK), status, started_at, completed_at, error_message
# alerts: id, scrape_result_id (FK), watch_query_id (FK), is_read, created_at
# app_settings: id, default_schedule, updated_at
```

### Test Fixture Pattern
```python
# backend/tests/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.models.base import Base

@pytest_asyncio.fixture
async def db_session():
    """Provide a clean async database session for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()
```

### Verifying SQLite PRAGMAs in Tests
```python
# Verification that WAL mode and busy_timeout are correctly set
async def test_sqlite_pragmas(db_session: AsyncSession):
    result = await db_session.execute(text("PRAGMA journal_mode"))
    journal_mode = result.scalar()
    assert journal_mode == "wal"

    result = await db_session.execute(text("PRAGMA busy_timeout"))
    timeout = result.scalar()
    assert timeout == 5000
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.x `Column()` | SQLAlchemy 2.0 `mapped_column()` + `Mapped[T]` | SQLAlchemy 2.0 (Jan 2023) | Full IDE type inference, mypy compatibility |
| `declarative_base()` function | `class Base(DeclarativeBase)` | SQLAlchemy 2.0 | Cleaner, supports type annotations |
| `sessionmaker()` + sync | `async_sessionmaker()` + `AsyncSession` | SQLAlchemy 1.4+ (refined in 2.0) | Native async support |
| Alembic `init` (sync template) | `alembic init -t async` | Alembic 1.7+ | Dedicated async template with proper env.py |
| `@app.on_event("startup")` | `@asynccontextmanager lifespan` | FastAPI 0.93+ | Deprecated events replaced by lifespan |

**Deprecated/outdated:**
- `declarative_base()` function: Use `class Base(DeclarativeBase)` instead
- `Column()` style: Use `mapped_column()` with `Mapped[T]`
- `@app.on_event("startup/shutdown")`: Use lifespan context manager
- Greenlet-based implicit async: SQLAlchemy 2.0.48 no longer installs greenlet by default

## Open Questions

1. **In-memory SQLite for tests vs. file-based**
   - What we know: In-memory (`sqlite+aiosqlite:///:memory:`) is fastest and provides natural isolation
   - What's unclear: WAL mode does not apply to in-memory databases -- PRAGMA verification tests may need a file-based test DB
   - Recommendation: Use in-memory for most repository tests; create a separate file-based fixture for PRAGMA verification tests specifically

2. **Seeding default app_settings row**
   - What we know: The table uses a single-row pattern; code that reads settings will fail if the row doesn't exist
   - What's unclear: Whether to seed in migration, in lifespan, or on first access
   - Recommendation: Seed in the initial Alembic migration using `op.execute()` -- this ensures the row exists before any code runs and is part of the migration history

3. **Alembic programmatic upgrade in async lifespan**
   - What we know: `alembic.command.upgrade()` is synchronous; the FastAPI lifespan is async
   - What's unclear: Whether running sync alembic command inside async lifespan blocks the event loop
   - Recommendation: This is fine for startup -- the app is not yet serving requests. Alembic's `command.upgrade()` runs to completion before `yield`, so no concurrency concern. Alternatively, use `asyncio.to_thread()` to be safe.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 1.3.0 |
| Config file | `backend/pytest.ini` or `backend/pyproject.toml` [tool.pytest] -- Wave 0 |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SC-1 | Six models create via Alembic migration | integration | `cd backend && python -m pytest tests/test_migrations.py -x` | No -- Wave 0 |
| SC-2 | CRUD watch queries + retailer URLs against live SQLite | unit | `cd backend && python -m pytest tests/repositories/test_watch_query.py -x` | No -- Wave 0 |
| SC-3 | WAL mode + busy_timeout on every connection | unit | `cd backend && python -m pytest tests/test_database.py::test_sqlite_pragmas -x` | No -- Wave 0 |
| SC-4 | Prices stored as integer cents (no floats) | unit | `cd backend && python -m pytest tests/repositories/test_watch_query.py::test_price_as_cents -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/conftest.py` -- async DB session fixture (in-memory + file-based)
- [ ] `backend/tests/repositories/test_watch_query.py` -- CRUD tests (SC-2, SC-4)
- [ ] `backend/tests/test_database.py` -- PRAGMA verification (SC-3)
- [ ] `backend/tests/test_migrations.py` -- Alembic migration smoke test (SC-1)
- [ ] `backend/pyproject.toml` or `backend/pytest.ini` -- pytest + pytest-asyncio config
- [ ] Framework install: `pip install pytest pytest-asyncio`

## Sources

### Primary (HIGH confidence)
- [SQLAlchemy 2.0 Async Docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) -- async engine, session factory, event listener patterns
- [SQLAlchemy SQLite Dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) -- aiosqlite driver configuration
- [Alembic Batch Migrations](https://alembic.sqlalchemy.org/en/latest/batch.html) -- render_as_batch for SQLite
- [Alembic Async Template](https://github.com/sqlalchemy/alembic/blob/main/alembic/templates/async/env.py) -- official async env.py
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) -- init, autogenerate, upgrade workflow
- [PyPI SQLAlchemy](https://pypi.org/project/SQLAlchemy) -- version 2.0.48, released 2026-03-02
- [PyPI alembic](https://pypi.org/project/alembic/) -- version 1.18.4, released 2026-02-10
- [PyPI aiosqlite](https://pypi.org/project/aiosqlite/) -- version 0.22.1, released 2025-12-23
- [PyPI pydantic-settings](https://pypi.org/project/pydantic-settings/) -- version 2.13.1, released 2026-02-19

### Secondary (MEDIUM confidence)
- [FastAPI Async SQLAlchemy Example](https://github.com/seapagan/fastapi_async_sqlalchemy2_example) -- real-world project structure reference
- [SQLite WAL Mode Docs](https://www.sqlite.org/wal.html) -- WAL behavior and limitations
- [Alembic Cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html) -- async migration patterns

### Tertiary (LOW confidence)
- [pytest-asyncio PyPI](https://pypi.org/project/pytest-asyncio/) -- version 1.3.0; verify fixture scope behavior for session-scoped loops

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages are mature, well-documented, verified on PyPI
- Architecture: HIGH -- patterns taken from official SQLAlchemy/Alembic docs and confirmed against real projects
- Pitfalls: HIGH -- documented in official SQLAlchemy async docs and confirmed by community reports

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable ecosystem, 30-day validity)
