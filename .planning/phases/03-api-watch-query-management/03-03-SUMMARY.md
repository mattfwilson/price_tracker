---
phase: 03-api-watch-query-management
plan: 03
subsystem: api
tags: [fastapi, scraping, pydantic, browser-manager, price-delta]

# Dependency graph
requires:
  - phase: 03-api-watch-query-management/03-02
    provides: "Watch query CRUD endpoints and repository layer"
  - phase: 02-scraping-engine
    provides: "BrowserManager, scrape_single_url, run_scrape_job, calculate_price_delta, ScrapeData"
provides:
  - "POST /watch-queries/{id}/scrape endpoint with lazy BrowserManager and price deltas"
  - "GET /retailer-urls/{id}/history endpoint with consecutive-pair delta computation"
  - "Pydantic response schemas: ScrapeResultResponse, ScrapeJobResponse, HistoryRecordResponse"
  - "Extended calculate_price_delta() with optional previous_price_cents parameter"
affects: [05-frontend-dashboard, 04-scheduling-alerts]

# Tech tracking
tech-stack:
  added: []
  patterns: [lazy-singleton-browser, consecutive-pair-delta, previous-price-bypass]

key-files:
  created:
    - backend/app/schemas/scrape.py
  modified:
    - backend/app/api/scrapes.py
    - backend/app/services/scrape_service.py
    - backend/tests/api/test_scrapes.py

key-decisions:
  - "Lazy singleton BrowserManager initialized on first scrape request, not at app boot"
  - "Trigger endpoint queries second-latest result (excluding current) for correct delta computation"
  - "History endpoint marks oldest record as 'new' directly rather than DB lookup"

patterns-established:
  - "Lazy singleton: module-level _browser_manager with async get_browser_manager() factory"
  - "Consecutive-pair delta: pass previous_price_cents to skip DB lookup in ordered history"

requirements-completed: [SCRAPE-03]

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 3 Plan 3: Scrape Trigger & History Endpoints Summary

**On-demand scrape trigger with lazy BrowserManager and price history endpoint computing consecutive-pair deltas via calculate_price_delta()**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-19T03:19:29Z
- **Completed:** 2026-03-19T03:22:41Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- POST /watch-queries/{id}/scrape triggers synchronous scrape with mocked browser, returns job status and results with price deltas
- GET /retailer-urls/{id}/history returns newest-first history with direction/delta_cents/pct_change per record
- Extended calculate_price_delta() with backward-compatible optional previous_price_cents parameter
- All 4 scrape/history tests pass with mocked BrowserManager; full suite 90 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend calculate_price_delta, create schemas, implement endpoints** - `dc8fb74` (feat)
2. **Bug fix: Correct delta computation for newly created results** - `a8b1910` (fix)
3. **Task 2: Implement scrape trigger and history tests** - `c3f2894` (test)

## Files Created/Modified
- `backend/app/schemas/scrape.py` - ScrapeResultResponse, ScrapeJobResponse, HistoryRecordResponse Pydantic schemas
- `backend/app/api/scrapes.py` - POST trigger and GET history endpoints with lazy BrowserManager singleton
- `backend/app/services/scrape_service.py` - calculate_price_delta extended with optional previous_price_cents
- `backend/tests/api/test_scrapes.py` - 4 tests: trigger scrape, trigger 404, history with deltas, empty history

## Decisions Made
- Lazy singleton BrowserManager initialized on first scrape request (not at app boot) to avoid browser startup cost when not needed
- Trigger endpoint queries for second-latest result (excluding the just-created one) to compute correct delta against the actual previous price
- History endpoint marks the oldest record as "new" directly rather than calling calculate_price_delta with DB lookup (which would find a newer record and produce wrong results)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed delta computation in trigger endpoint finding its own result**
- **Found during:** Task 2 (test_trigger_scrape)
- **Issue:** calculate_price_delta() DB lookup found the just-flushed result as "latest", comparing price to itself and returning "unchanged" instead of "new"
- **Fix:** Query second-latest result (excluding current result id) and pass as previous_price_cents; handle no-previous case as "new" directly
- **Files modified:** backend/app/api/scrapes.py
- **Verification:** test_trigger_scrape passes with direction="new" for first scrape
- **Committed in:** a8b1910

**2. [Rule 1 - Bug] Fixed history oldest record delta using wrong comparison**
- **Found during:** Task 2 (test_get_history)
- **Issue:** Oldest history record called calculate_price_delta with previous_price_cents=None, triggering DB lookup that found the newest record (not the one before it), producing "higher" instead of "new"
- **Fix:** Return direction="new" directly for the oldest record instead of DB lookup
- **Files modified:** backend/app/api/scrapes.py
- **Verification:** test_get_history passes with oldest record direction="new"
- **Committed in:** a8b1910

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correct delta computation when results already exist in session. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 3 API surface complete: full CRUD + scrape trigger + price history
- Ready for Phase 4 (scheduling and alerts) and Phase 5 (frontend dashboard)
- All 90 tests pass, full suite green

---
*Phase: 03-api-watch-query-management*
*Completed: 2026-03-18*
