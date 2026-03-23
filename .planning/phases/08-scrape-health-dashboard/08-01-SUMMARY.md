---
phase: 08-scrape-health-dashboard
plan: "01"
subsystem: backend
tags: [health-tracking, scrape-monitoring, sqlalchemy, fastapi, alembic]
dependency_graph:
  requires:
    - "Phase 02: scraping engine with ScrapeError/FailureType"
    - "Phase 01: RetailerUrl and WatchQuery models"
    - "Migration a3b7c9d1e4f2: alert enhancement columns (down_revision)"
  provides:
    - "ScrapeUrlAttempt model and scrape_url_attempts table"
    - "create_scrape_url_attempt repository function"
    - "get_health_stats_for_all_urls repository function"
    - "GET /scrape-health/urls API endpoint"
    - "GET /scrape-health/query/{id} API endpoint"
  affects:
    - "backend/app/services/scrape_service.py: every scrape attempt now recorded"
    - "Plans 02 and 03: frontend health page and QueryCard dots consume this data"
tech_stack:
  added:
    - "ScrapeUrlAttempt SQLAlchemy model with scraped_at, is_success, error_type, error_message"
    - "SQL window functions (row_number OVER PARTITION BY) for last-10 window per URL"
    - "Alembic migration b5e1f3a8c7d9 with composite index on (retailer_url_id, scraped_at DESC)"
  patterns:
    - "TDD: RED tests written before implementation, GREEN verified with 22 passing tests"
    - "Repository pattern: health stat computation via SQL not Python loops"
    - "Separate ScrapeError/Exception clauses for typed error_type recording"
key_files:
  created:
    - backend/app/models/scrape_url_attempt.py
    - backend/alembic/versions/b5e1f3a8c7d9_add_scrape_url_attempts.py
    - backend/app/repositories/scrape_url_attempt.py
    - backend/app/schemas/health.py
    - backend/app/api/health.py
    - backend/tests/repositories/test_scrape_url_attempt.py
    - backend/tests/api/test_health.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/services/scrape_service.py
    - backend/main.py
    - backend/tests/test_migrations.py
decisions:
  - "Used /scrape-health prefix (not /health) to avoid collision with existing GET /health server check"
  - "Consecutive failures computed in Python after SQL window query (simpler than correlated subquery in SQLite)"
  - "last_success_at looks across ALL attempts (not just window) per plan spec"
  - "Copied missing a3b7c9d1e4f2 migration to worktree (it existed in main but not worktree branch)"
metrics:
  duration: "5min"
  completed: "2026-03-23"
  tasks_completed: 2
  files_created: 7
  files_modified: 4
---

# Phase 08 Plan 01: Scrape Health Backend Summary

ScrapeUrlAttempt model, Alembic migration, SQL window-function health stats repository, scrape service attempt recording, and GET /scrape-health/urls|query API with 22 TDD-passing tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Data model, migration, repository, scrape service | 73bf9be | scrape_url_attempt.py, b5e1f3a8c7d9 migration, repository, scrape_service.py |
| 2 | Health API endpoint and Pydantic schemas | e92f893 | health.py schema, health.py API, main.py, test_migrations.py |

## What Was Built

The complete backend infrastructure for scrape health tracking:

1. **ScrapeUrlAttempt model** - Records every scrape attempt per URL with `scraped_at`, `is_success`, `error_type` (nullable), `error_message` (nullable). No TimestampMixin - only `scraped_at` needed.

2. **Alembic migration b5e1f3a8c7d9** - Creates `scrape_url_attempts` table with composite index on `(retailer_url_id, scraped_at DESC)` for efficient window queries. Down-revision from `a3b7c9d1e4f2`.

3. **Repository** - `create_scrape_url_attempt` for INSERT+flush. `get_health_stats_for_all_urls` uses SQL `row_number() OVER (PARTITION BY retailer_url_id ORDER BY scraped_at DESC)` to cap the window at 10 attempts per URL, then aggregates success_count and window_size. Status thresholds: >=80% = healthy, >=50% = degraded, <50% = failing. Consecutive failures computed in Python from ranked rows.

4. **Scrape service integration** - `except (ScrapeError, Exception)` replaced with two separate clauses: `except ScrapeError as e` records `e.failure_type.value` as error_type; `except Exception as e` records `type(e).__name__`. Success path records `is_success=True`.

5. **Health API** - `/scrape-health/urls` returns all URL health stats. `/scrape-health/query/{watch_query_id}` filters to one query's URLs for QueryCard use in Plan 03. Uses `/scrape-health` prefix to avoid collision with existing `/health` server check.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_migration_creates_all_tables expected 6 tables**
- **Found during:** Task 2 verification
- **Issue:** Migration test hardcoded expected table count as 6; new migration adds scrape_url_attempts making it 7
- **Fix:** Updated expected list to include "scrape_url_attempts"
- **Files modified:** backend/tests/test_migrations.py
- **Commit:** e92f893

**2. [Rule 3 - Missing dependency] a3b7c9d1e4f2 migration not in worktree**
- **Found during:** Task 1 setup
- **Issue:** Worktree branch only had initial migration; a3b7c9d1e4f2 existed in main repo but not worktree
- **Fix:** Copied migration file to worktree before creating the dependent b5e1f3a8c7d9 migration
- **Files modified:** backend/alembic/versions/a3b7c9d1e4f2_add_alert_enhancement_columns.py (copied)
- **Commit:** ce9e0fc (included in RED commit)

## Known Stubs

None - all health stats are computed from real database data.

## Pre-existing Test Failures (Deferred)

14 pre-existing failures unrelated to Plan 01 work:
- `tests/scrapers/test_extractors.py`: 8 failures (MagicMock vs AsyncMock in mock setup)
- `tests/scrapers/test_retry.py`: 5 failures (same root cause)
- `tests/services/test_scheduler.py::test_schedule_map_keys`: 1 failure (new schedule options added in Phase 06 not reflected in test)

Logged in `.planning/phases/08-scrape-health-dashboard/deferred-items.md`.

## Self-Check: PASSED

Files created:
- backend/app/models/scrape_url_attempt.py: FOUND
- backend/alembic/versions/b5e1f3a8c7d9_add_scrape_url_attempts.py: FOUND
- backend/app/repositories/scrape_url_attempt.py: FOUND
- backend/app/schemas/health.py: FOUND
- backend/app/api/health.py: FOUND
- backend/tests/repositories/test_scrape_url_attempt.py: FOUND
- backend/tests/api/test_health.py: FOUND

Commits:
- ce9e0fc: test(08-01): add failing tests for ScrapeUrlAttempt repository - FOUND
- 73bf9be: feat(08-01): ScrapeUrlAttempt model, migration, repository, and scrape service integration - FOUND
- 18efbd4: test(08-01): add failing tests for health API endpoints - FOUND
- e92f893: feat(08-01): health API endpoint with Pydantic schemas and router registration - FOUND
