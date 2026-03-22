---
phase: 07-advanced-alert-enhancements
plan: 01
subsystem: api
tags: [alerts, sqlalchemy, alembic, pydantic, cooldown, percentage-drop]

requires:
  - phase: 04-scheduling-alerts
    provides: alert evaluation pipeline, Alert model, should_fire_alert
provides:
  - Alembic migration adding pct_drop_threshold, alert_cooldown_hours, alert_type columns
  - get_rolling_avg_price and get_all_time_min_price repository functions
  - is_within_cooldown repository function
  - should_fire_pct_drop_alert service function
  - Cooldown-aware evaluate_alerts_for_job with alert_type support
affects: [07-02, 07-03, frontend alert display]

tech-stack:
  added: []
  patterns: [cooldown guard before alert loop, alert_type discriminator on Alert model]

key-files:
  created:
    - backend/alembic/versions/a3b7c9d1e4f2_add_alert_enhancement_columns.py
  modified:
    - backend/app/models/watch_query.py
    - backend/app/models/alert.py
    - backend/app/schemas/watch_query.py
    - backend/app/repositories/watch_query.py
    - backend/app/repositories/scrape_result.py
    - backend/app/repositories/alert.py
    - backend/app/services/alert_service.py
    - backend/tests/repositories/test_scrape_result.py
    - backend/tests/services/test_alert_service.py

key-decisions:
  - "Cooldown check runs once before the per-result loop, not per-result, to avoid partial alert sets"
  - "alert_type is 'pct_drop' only when pct fires and threshold does not -- dual-fire uses 'threshold'"
  - "Used batch_alter_table for SQLite-compatible column additions in migration"

patterns-established:
  - "Cooldown guard pattern: check is_within_cooldown before alert evaluation loop"
  - "Rolling average query with configurable window_days parameter"

requirements-completed: [ALERT-05, ALERT-07]

duration: 5min
completed: 2026-03-22
---

# Phase 7 Plan 1: Alert Enhancement Backend Summary

**Percentage-drop alerts firing when price is X% below 30-day rolling avg, with configurable cooldown suppression and alert_type discriminator**

## Performance

- **Duration:** 5min
- **Started:** 2026-03-22T22:17:04Z
- **Completed:** 2026-03-22T22:22:04Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Alembic migration adds pct_drop_threshold (Float, nullable), alert_cooldown_hours (Integer, default 24), and alert_type (String, default "threshold") columns
- Rolling average and all-time min price repository queries with full test coverage
- Alert cooldown prevents duplicate alerts within configurable window (0 = disabled)
- Percentage-drop alerts fire when current price drops below configured % of 30-day rolling avg (min 3 samples)

## Task Commits

Each task was committed atomically:

1. **Task 1: Alembic migration + model/schema/repo extensions** - `87171e4` (test: RED) -> `1642e04` (feat: GREEN)
2. **Task 2: Alert service cooldown + pct drop logic** - `d8a7609` (test: RED) -> `4c689ec` (feat: GREEN)

_TDD approach: each task has separate test (RED) and implementation (GREEN) commits._

## Files Created/Modified
- `backend/alembic/versions/a3b7c9d1e4f2_add_alert_enhancement_columns.py` - Migration adding 3 columns
- `backend/app/models/watch_query.py` - Added pct_drop_threshold, alert_cooldown_hours fields
- `backend/app/models/alert.py` - Added alert_type field
- `backend/app/schemas/watch_query.py` - Extended Create/Update/Response/Detail schemas with new fields + validators
- `backend/app/repositories/watch_query.py` - create_watch_query/update_watch_query accept new fields
- `backend/app/repositories/scrape_result.py` - Added get_rolling_avg_price, get_all_time_min_price
- `backend/app/repositories/alert.py` - Added is_within_cooldown, create_alert accepts alert_type
- `backend/app/services/alert_service.py` - Added should_fire_pct_drop_alert, cooldown in evaluate_alerts_for_job
- `backend/tests/repositories/test_scrape_result.py` - TestRollingAvg, TestAllTimeLow, TestIsWithinCooldown
- `backend/tests/services/test_alert_service.py` - TestPctDropAlert, TestCooldown classes

## Decisions Made
- Cooldown check runs once before the per-result loop (not per-result) to avoid partial alert sets within a single job
- alert_type is "pct_drop" only when percentage check fires and threshold check does not; dual-fire defaults to "threshold"
- Used batch_alter_table for SQLite-compatible column additions in migration
- SSE payload includes alert_type field for frontend consumption

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed cooldown test data setup for re-breach detection**
- **Found during:** Task 2 (TestCooldown tests)
- **Issue:** Test expected alerts but existing should_fire_alert re-breach detection requires price recovery above threshold before a new breach fires; test data had consecutive below-threshold prices
- **Fix:** Added price recovery step (1200 cents) between old breach and new breach in cooldown tests
- **Files modified:** backend/tests/services/test_alert_service.py
- **Verification:** All 16 alert service tests pass
- **Committed in:** 4c689ec (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix in test setup)
**Impact on plan:** Test data corrected to match existing re-breach detection semantics. No scope creep.

## Issues Encountered
None beyond the test data correction noted above.

## Known Stubs
None - all functions are fully wired with real data sources.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Backend data layer and alert evaluation logic complete for percentage-drop and cooldown
- Ready for Plan 02 (frontend alert configuration UI) and Plan 03 (API endpoint integration)
- WatchQueryDetailResponse includes is_all_time_low field (currently defaults to False, to be wired in Plan 02/03)

---
*Phase: 07-advanced-alert-enhancements*
*Completed: 2026-03-22*
