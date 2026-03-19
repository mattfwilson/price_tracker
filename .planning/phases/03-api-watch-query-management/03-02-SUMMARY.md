---
phase: 03-api-watch-query-management
plan: 02
subsystem: api
tags: [fastapi, crud, pydantic, sqlalchemy, async]

# Dependency graph
requires:
  - phase: 03-api-watch-query-management/03-01
    provides: "POST /watch-queries/ endpoint, repository layer, base schemas, test infrastructure"
  - phase: 02-scraping-engine
    provides: "scrape_result repository with get_latest_scrape_result, scrape_service with calculate_price_delta"
provides:
  - "Complete watch query CRUD: GET list, GET detail, PATCH update, DELETE"
  - "Embedded latest scrape results with price delta in GET detail response"
  - "Diff-based URL replacement preserving scrape history"
  - "Pause/resume toggle via PATCH is_active"
affects: [05-frontend-dashboard, 04-scheduling-alerts]

# Tech tracking
tech-stack:
  added: []
  patterns: [diff-based-url-replacement, embedded-latest-results, server-side-onupdate-refetch]

key-files:
  created: []
  modified:
    - backend/app/api/watch_queries.py
    - backend/app/schemas/watch_query.py
    - backend/app/repositories/watch_query.py
    - backend/tests/api/test_watch_queries.py

key-decisions:
  - "Diff-based URL replacement in PATCH to preserve scrape history for retained URLs"
  - "Re-fetch after flush in update_watch_query to resolve server-side onupdate staleness"
  - "Expire cached relationship state before re-query after URL replacement"

patterns-established:
  - "Diff-based URL replacement: only delete removed URLs, add new ones, preserving FK history"
  - "Server-side onupdate fields require re-fetch after flush to avoid MissingGreenlet"

requirements-completed: [QUERY-02, QUERY-03, QUERY-04, QUERY-05]

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 3 Plan 2: Watch Query CRUD Summary

**Full CRUD endpoints (list, detail with embedded scrape results, update with diff-based URL dedup, delete, pause/resume) and 12-test coverage**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T03:14:55Z
- **Completed:** 2026-03-19T03:17:44Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- GET /watch-queries/ returns all queries ordered by created_at desc
- GET /watch-queries/{id} returns query with embedded LatestScrapeResult per retailer URL including price delta
- PATCH /watch-queries/{id} updates scalar fields and replaces URLs with diff-based dedup preserving scrape history
- DELETE /watch-queries/{id} returns 204 with cascade cleanup
- Pause/resume via PATCH is_active toggle
- All 12 watch query tests pass (4 from Plan 01 + 8 newly implemented)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add response schemas and implement CRUD endpoints** - `9848bf6` (feat)
2. **Task 2: Unskip and implement all CRUD endpoint tests** - `d45fd13` (test)

## Files Created/Modified
- `backend/app/schemas/watch_query.py` - Added LatestScrapeResult, RetailerUrlWithLatest, WatchQueryDetailResponse schemas
- `backend/app/api/watch_queries.py` - Complete CRUD router: GET list, GET detail, PATCH update, DELETE
- `backend/app/repositories/watch_query.py` - Fixed update to re-fetch after flush for server-side onupdate
- `backend/tests/api/test_watch_queries.py` - 8 new tests: list, get detail, get 404, update, URL dedup, delete, delete 404, pause/resume

## Decisions Made
- Diff-based URL replacement in PATCH handler to preserve scrape history for retained URLs (avoids cascade delete-orphan destroying ScrapeResult records)
- Re-fetch query after flush in update_watch_query to resolve SQLAlchemy MissingGreenlet on server-side onupdate fields
- Expire cached relationship state before re-query after URL replacement to ensure fresh data

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MissingGreenlet on updated_at after update**
- **Found during:** Task 2 (test_update_watch_query)
- **Issue:** update_watch_query returned stale object after flush; server-side onupdate for updated_at triggered MissingGreenlet when Pydantic serialized response
- **Fix:** Re-fetch query via get_watch_query after flush in repository layer
- **Files modified:** backend/app/repositories/watch_query.py
- **Verification:** test_update_watch_query passes
- **Committed in:** d45fd13 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed stale relationship cache after URL replacement**
- **Found during:** Task 2 (test_update_watch_query_urls_with_dedup)
- **Issue:** After deleting/adding RetailerUrl objects and flushing, selectinload returned cached relationship data showing old URLs
- **Fix:** Added db.expire(query) before re-fetching to clear identity map cache
- **Files modified:** backend/app/api/watch_queries.py
- **Verification:** test_update_watch_query_urls_with_dedup passes
- **Committed in:** d45fd13 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correct SQLAlchemy async behavior. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full watch query CRUD surface complete for frontend consumption in Phase 5
- Ready for Plan 03-03 (scrape execution endpoints if applicable)
- All 86 tests pass (4 skipped browser-dependent tests), full suite green

---
*Phase: 03-api-watch-query-management*
*Completed: 2026-03-18*
