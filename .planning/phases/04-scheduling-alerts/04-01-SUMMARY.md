---
phase: 04-scheduling-alerts
plan: 01
subsystem: scheduling, alerts
tags: [apscheduler, asyncio, sse, alerts, scheduler]

# Dependency graph
requires:
  - phase: 03-api-watch-queries
    provides: Watch query CRUD endpoints, scrape trigger, scrape service
provides:
  - APScheduler AsyncIOScheduler singleton with configurable intervals
  - Alert evaluation service with re-breach detection logic
  - Alert repository (create, count, list, mark-read, dismiss-all)
  - Alert Pydantic schemas (AlertResponse, AlertSSEPayload, UnreadCountResponse)
  - SSE broadcast stub for real-time alert delivery
  - Scheduler-route sync on watch query create/update/delete
affects: [04-02-alert-endpoints, 04-03-sse-streaming, 05-frontend]

# Tech tracking
tech-stack:
  added: [APScheduler 3.11]
  patterns: [scheduler singleton, re-breach detection, SSE client queue set]

key-files:
  created:
    - backend/app/services/scheduler.py
    - backend/app/services/alert_service.py
    - backend/app/repositories/alert.py
    - backend/app/schemas/alert.py
    - backend/tests/services/test_scheduler.py
    - backend/tests/services/test_alert_service.py
    - backend/tests/repositories/test_alert.py
  modified:
    - backend/pyproject.toml
    - backend/main.py
    - backend/app/api/watch_queries.py
    - backend/app/api/scrapes.py

key-decisions:
  - "AsyncIOScheduler started paused=False in lifespan after register_jobs_from_db"
  - "Re-breach detection uses offset(1) to skip current result when checking previous price"
  - "SSE broadcast stub with asyncio.Queue set ready for Plan 03 streaming endpoints"
  - "Alerts router import wrapped in try/except for forward-compatibility with Plan 02"

patterns-established:
  - "Scheduler sync: route handlers call add_scrape_job/remove_scrape_job after DB mutation"
  - "Re-breach logic: first breach fires, continued breach skips, re-breach fires"
  - "Lazy imports in scheduled_scrape to avoid circular dependency between scheduler and scrape_service"

requirements-completed: [SCRAPE-02, ALERT-01]

# Metrics
duration: 5min
completed: 2026-03-19
---

# Phase 4 Plan 1: Scheduling & Alert Evaluation Summary

**APScheduler background scheduling with configurable intervals and alert evaluation using re-breach detection logic**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-19T03:59:22Z
- **Completed:** 2026-03-19T04:04:18Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- APScheduler AsyncIOScheduler singleton with SCHEDULE_MAP (every_6h, every_12h, daily, weekly)
- Alert evaluation service with first-breach/continued-breach/re-breach detection
- Alert repository with full CRUD (create, unread count, list, mark read, dismiss all)
- Scheduler integrated into FastAPI lifespan (register on boot, shutdown on exit)
- Watch query CRUD routes sync scheduler state on create/pause/resume/delete/schedule-change
- On-demand scrape trigger also evaluates alerts
- 20 new tests, 110 total tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Scheduler service, alert evaluation, repository, schemas** - `a809cdb` (test: RED), `2441ea7` (feat: GREEN)
2. **Task 2: Lifespan integration and route hooks** - `a61b238` (feat)

_TDD task had separate test and implementation commits._

## Files Created/Modified
- `backend/app/services/scheduler.py` - APScheduler singleton, SCHEDULE_MAP, job management, scheduled_scrape
- `backend/app/services/alert_service.py` - should_fire_alert re-breach logic, evaluate_alerts_for_job, SSE broadcast stub
- `backend/app/repositories/alert.py` - Alert CRUD repository functions
- `backend/app/schemas/alert.py` - AlertResponse, AlertSSEPayload, UnreadCountResponse Pydantic models
- `backend/pyproject.toml` - Added APScheduler dependency, updated FastAPI minimum
- `backend/main.py` - Scheduler lifespan integration, alerts router mount
- `backend/app/api/watch_queries.py` - Scheduler sync on create/update/delete
- `backend/app/api/scrapes.py` - Alert evaluation after on-demand scrape
- `backend/tests/services/test_scheduler.py` - 7 scheduler tests
- `backend/tests/services/test_alert_service.py` - 7 alert service tests
- `backend/tests/repositories/test_alert.py` - 6 alert repository tests

## Decisions Made
- AsyncIOScheduler fixture uses `start(paused=True)` for tests to avoid actual job execution
- Re-breach detection queries previous result using `offset(1)` to skip the just-flushed current result
- SSE client management uses `set[asyncio.Queue]` with `put_nowait` and `QueueFull` handling
- Alerts router import uses try/except ImportError for forward-compatibility until Plan 02 creates it
- Monkeypatch targets `app.core.database.async_session_factory` (source module) not scheduler module for register_jobs_from_db test

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] APScheduler pip install required direct PyPI index**
- **Found during:** Task 1 (dependency installation)
- **Issue:** Default pip index did not find APScheduler package
- **Fix:** Used `--index-url https://pypi.org/simple/` to install directly from PyPI
- **Verification:** `import apscheduler` succeeds
- **Committed in:** 2441ea7 (part of Task 1 GREEN commit)

**2. [Rule 1 - Bug] AsyncIOScheduler fixture needed async context for event loop**
- **Found during:** Task 1 (test execution)
- **Issue:** `scheduler.start(paused=True)` requires running event loop, sync fixture had none
- **Fix:** Changed `@pytest.fixture` to `@pytest_asyncio.fixture` and made test methods async
- **Verification:** All scheduler tests pass
- **Committed in:** 2441ea7 (part of Task 1 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Scheduler and alert evaluation core complete
- Ready for Plan 02 (alert CRUD endpoints) and Plan 03 (SSE streaming)
- SSE broadcast stub wired and ready for client connections

---
*Phase: 04-scheduling-alerts*
*Completed: 2026-03-19*
