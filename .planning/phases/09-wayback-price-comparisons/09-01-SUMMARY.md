---
phase: 09-wayback-price-comparisons
plan: "01"
subsystem: backend
tags: [repository, api, schema, wayback, price-history]
dependency_graph:
  requires: [backend/app/repositories/scrape_result.py, backend/app/schemas/watch_query.py, backend/app/api/watch_queries.py]
  provides: [get_price_near_date, get_all_time_extremes_for_url, get_rolling_avg_price, wayback fields in detail endpoint]
  affects: [GET /watch-queries/{id} response, RetailerUrlWithLatest schema]
tech_stack:
  added: []
  patterns: [SQLite julianday for nearest-date ordering, tuple return for paired stats]
key_files:
  created: []
  modified:
    - backend/app/repositories/scrape_result.py
    - backend/tests/repositories/test_scrape_result.py
    - backend/app/schemas/watch_query.py
    - backend/app/api/watch_queries.py
decisions:
  - get_rolling_avg_price and get_all_time_min_price added alongside new functions (were referenced as existing in plan context but absent from worktree branch)
  - SQLite julianday function used for nearest-date proximity ordering (no abs() in SQLAlchemy core, func.abs wraps func.julianday difference)
  - All wayback fields optional/None by default for backward-compatible response
metrics:
  duration: 4min
  completed: "2026-03-23"
  tasks: 2
  files: 4
---

# Phase 9 Plan 01: Wayback Price Comparisons Backend Summary

Backend wayback price comparison logic: new repository functions for nearest-date price lookup and per-URL all-time extremes/rolling averages, extended RetailerUrlWithLatest schema with 10 optional wayback fields, wired into the existing GET /watch-queries/{id} detail endpoint.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add repository functions with tests (TDD) | 6c20bc4 | scrape_result.py, test_scrape_result.py |
| 2 | Extend schema and wire detail endpoint | a1b6654 | watch_query.py, watch_queries.py |

## What Was Built

### Task 1: Repository Functions (TDD)

Four new async functions in `backend/app/repositories/scrape_result.py`:

- `get_rolling_avg_price(session, retailer_url_id, window_days=30)` - Returns `(avg_price_cents, count)` for results within a rolling window. Supports both 30 and 90 day windows.
- `get_all_time_min_price(session, watch_query_id)` - Returns minimum price across all URLs for a watch query.
- `get_price_near_date(session, retailer_url_id, target_date, max_delta_days=7)` - Returns `(price_cents, actual_date)` for the result nearest to `target_date` within `+/- max_delta_days` using SQLite `julianday` ordering.
- `get_all_time_extremes_for_url(session, retailer_url_id)` - Returns `(all_time_low_cents, all_time_high_cents)` for a single URL.

Test coverage: 10 new tests across `TestRollingAvg`, `TestPriceNearDate`, `TestAllTimeExtremes` classes. All 16 repository tests pass.

### Task 2: Schema Extension and Endpoint Wiring

Extended `RetailerUrlWithLatest` with 10 optional fields:
`price_30d_cents`, `date_30d`, `price_90d_cents`, `date_90d`, `avg_30d_cents`, `avg_30d_count`, `avg_90d_cents`, `avg_90d_count`, `all_time_low_cents`, `all_time_high_cents`

Detail endpoint `GET /watch-queries/{id}` now computes and embeds all wayback stats per retailer URL. Response is backward-compatible (all new fields default to `None`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Missing Prerequisites] Added get_rolling_avg_price and get_all_time_min_price**
- **Found during:** Task 1 setup
- **Issue:** Plan context block listed `get_rolling_avg_price` and `get_all_time_min_price` as "existing" functions, but they were absent from the worktree branch (which is behind main by several commits)
- **Fix:** Implemented both functions alongside the two new functions specified in the plan
- **Files modified:** `backend/app/repositories/scrape_result.py`
- **Commit:** 6c20bc4

### Pre-existing Test Failures (Out of Scope)

- `tests/api/test_scrapes.py::test_trigger_scrape` - Fails due to patchright Chrome browser conflict with existing Chrome session. Pre-existing on this branch, unrelated to this plan's changes.
- `tests/scrapers/test_extractors.py::test_bestbuy_extract_json_ld` - TypeError in BestBuy scraper mock. Pre-existing on this branch, unrelated to this plan's changes.

Both logged to deferred items - not caused by this plan.

## Verification

- `cd backend && python -m pytest tests/repositories/test_scrape_result.py -x -q` - 16 passed
- `cd backend && python -m pytest tests/repositories/ tests/api/test_watch_queries.py -q` - 41 passed

## Known Stubs

None. All wayback fields are computed from real data (or None when no data exists). No placeholders or hardcoded values.

## Self-Check: PASSED
