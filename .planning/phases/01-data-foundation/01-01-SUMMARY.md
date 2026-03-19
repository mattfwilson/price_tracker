---
phase: 01-data-foundation
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, sqlite, asyncio, pydantic-settings, fastapi]

# Dependency graph
requires: []
provides:
  - Six SQLAlchemy 2.0 async models (WatchQuery, RetailerUrl, ScrapeResult, ScrapeJob, Alert, AppSettings)
  - Async database engine with SQLite WAL mode and busy_timeout PRAGMAs
  - Alembic migration infrastructure with initial schema migration
  - FastAPI app entry point with lifespan migration runner
  - Pydantic BaseSettings configuration with PRICE_SCRAPER_ env prefix
affects: [02-scraping-engine, 03-api, 04-scheduling-alerts]

# Tech tracking
tech-stack:
  added: [sqlalchemy 2.0.48, alembic 1.18.4, aiosqlite 0.22.1, pydantic-settings 2.13.1, fastapi 0.135.1]
  patterns: [async-sessionmaker, PRAGMA-event-listener, render_as_batch, lifespan-migration, integer-cents-pricing]

key-files:
  created:
    - backend/pyproject.toml
    - backend/app/core/config.py
    - backend/app/core/database.py
    - backend/app/models/base.py
    - backend/app/models/watch_query.py
    - backend/app/models/retailer_url.py
    - backend/app/models/scrape_result.py
    - backend/app/models/scrape_job.py
    - backend/app/models/alert.py
    - backend/app/models/app_settings.py
    - backend/app/models/__init__.py
    - backend/alembic/env.py
    - backend/alembic/versions/6e00987c7dbb_initial_schema_six_tables.py
    - backend/main.py
  modified: []

key-decisions:
  - "Python 3.10+ (lowered from 3.11 to match local environment)"
  - "Added setuptools package discovery config to handle flat layout with alembic/data dirs"
  - "Seeded app_settings default row in initial Alembic migration"

patterns-established:
  - "Integer cents for all prices (threshold_cents, price_cents) -- never Float"
  - "TimestampMixin with server_default=func.now() and onupdate=func.now()"
  - "PRAGMA event listener on sync_engine for WAL and busy_timeout"
  - "async_sessionmaker with expire_on_commit=False"
  - "render_as_batch=True in all Alembic context.configure() calls"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-03-18
---

# Phase 1 Plan 1: Project Scaffold and Models Summary

**Six SQLAlchemy 2.0 async models with Alembic migration infrastructure, SQLite WAL+busy_timeout PRAGMAs, and FastAPI lifespan migration runner**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-19T00:41:25Z
- **Completed:** 2026-03-19T00:49:52Z
- **Tasks:** 2
- **Files modified:** 26

## Accomplishments
- All six SQLAlchemy models created with proper relationships, foreign keys, and integer-cent pricing
- Async database engine configured with WAL mode and busy_timeout=5000 PRAGMA listeners
- Alembic async migration infrastructure with render_as_batch=True for SQLite compatibility
- Initial migration auto-generated, seeds app_settings default row
- FastAPI main.py with lifespan that runs alembic upgrade head on startup

## Task Commits

Each task was committed atomically:

1. **Task 1: Project scaffold, config, database engine, and all six models** - `7b97880` (feat)
2. **Task 2: Alembic async setup, initial migration, and FastAPI lifespan** - `2f94b33` (feat)

## Files Created/Modified
- `backend/pyproject.toml` - Project metadata, dependencies, setuptools config
- `backend/.env.example` - Environment variable template
- `backend/.gitignore` - Ignores for db file, pycache, venv, env
- `backend/app/core/config.py` - Pydantic BaseSettings with PRICE_SCRAPER_ prefix
- `backend/app/core/database.py` - Async engine, PRAGMA listeners, session factory, get_db dependency
- `backend/app/models/base.py` - DeclarativeBase and TimestampMixin
- `backend/app/models/watch_query.py` - WatchQuery model with threshold_cents (Integer)
- `backend/app/models/retailer_url.py` - RetailerUrl model with FK to watch_queries
- `backend/app/models/scrape_result.py` - ScrapeResult model with price_cents (Integer), immutable (no TimestampMixin)
- `backend/app/models/scrape_job.py` - ScrapeJob model with status tracking
- `backend/app/models/alert.py` - Alert model linking scrape_result to watch_query
- `backend/app/models/app_settings.py` - AppSettings single-row config table
- `backend/app/models/__init__.py` - Imports all 6 models + Base for Alembic discovery
- `backend/alembic.ini` - Alembic config with SQLite URL
- `backend/alembic/env.py` - Async env.py with render_as_batch, sys.path fix, settings import
- `backend/alembic/versions/6e00987c7dbb_initial_schema_six_tables.py` - Initial migration + app_settings seed
- `backend/main.py` - FastAPI app with lifespan migration and /health endpoint
- `backend/app/__init__.py` - Empty package init
- `backend/app/core/__init__.py` - Empty package init
- `backend/app/repositories/__init__.py` - Empty package init
- `backend/app/services/__init__.py` - Empty package init
- `backend/app/api/__init__.py` - Empty package init
- `backend/app/schemas/__init__.py` - Empty package init
- `backend/data/.gitkeep` - Placeholder for SQLite data directory

## Decisions Made
- Lowered requires-python from >=3.11 to >=3.10 to match local Python environment
- Added `[tool.setuptools.packages.find] include = ["app*"]` to resolve flat-layout package discovery conflict with alembic/ and data/ directories
- Seeded default app_settings row (id=1, default_schedule='daily') directly in initial Alembic migration

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed setuptools flat-layout package discovery error**
- **Found during:** Task 1 (pip install -e ".[dev]")
- **Issue:** setuptools auto-discovery found multiple top-level packages (app, data, alembic) and refused to build
- **Fix:** Added `[tool.setuptools.packages.find] include = ["app*"]` to pyproject.toml
- **Files modified:** backend/pyproject.toml
- **Verification:** pip install -e . succeeds
- **Committed in:** 7b97880 (Task 1 commit)

**2. [Rule 3 - Blocking] Lowered Python version requirement from 3.11 to 3.10**
- **Found during:** Task 1 (pip install -e ".[dev]")
- **Issue:** Local Python is 3.10.18 but pyproject.toml specified >=3.11
- **Fix:** Changed requires-python to ">=3.10"
- **Files modified:** backend/pyproject.toml
- **Verification:** pip install -e . succeeds
- **Committed in:** 7b97880 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for basic installability. No scope creep.

## Issues Encountered
- Corporate pip index (Klaviyo JFrog) missing setuptools -- used --index-url https://pypi.org/simple/ for direct dependency installation
- pytest-asyncio 1.3.0 installed (latest compatible); asyncio_mode = "auto" configured in pyproject.toml

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All six models importable and Alembic-migratable
- Database infrastructure ready for repository layer (Plan 01-02)
- FastAPI app starts and auto-migrates, ready for API routes (Phase 3)

## Self-Check: PASSED

All 14 key files verified present. Both task commits (7b97880, 2f94b33) verified in git log.

---
*Phase: 01-data-foundation*
*Completed: 2026-03-18*
