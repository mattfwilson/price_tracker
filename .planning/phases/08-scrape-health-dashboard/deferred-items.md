# Deferred Items - Phase 08

## Pre-existing Test Failures (out of scope for 08-01)

These failures existed before any Phase 08 changes and are not caused by Plan 01 work.

### 1. tests/scrapers/test_extractors.py (8 failures)
- BestBuy, Walmart, Newegg, Microcenter extractor tests fail with TypeError
- Root cause: Test mocks use MagicMock instead of AsyncMock for coroutines
- Impact: Does not affect production code; mock setup issue in tests

### 2. tests/scrapers/test_retry.py (5 failures)
- Retry tests fail because mock objects aren't awaitable
- Same root cause as extractor tests: MagicMock vs AsyncMock

### 3. tests/services/test_scheduler.py::TestScheduleMap::test_schedule_map_keys
- SCHEDULE_MAP has extra keys ('every_1h', 'every_3h') added in Phase 06
- Test expected only 4 schedule options; now 6 exist
- Impact: Test needs updating to match new schedule options
