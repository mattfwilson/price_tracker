---
phase: 03-api-watch-query-management
verified: 2026-03-18T00:00:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 3: API Watch Query Management Verification Report

**Phase Goal:** Implement the FastAPI layer for watch query CRUD management, pause/resume control, on-demand scrape triggering, and price history retrieval.
**Verified:** 2026-03-18
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                               | Status     | Evidence                                                                      |
|----|-------------------------------------------------------------------------------------|------------|-------------------------------------------------------------------------------|
| 1  | FastAPI app starts with CORS middleware allowing localhost:5173 and localhost:3000   | VERIFIED   | `backend/main.py` lines 31-37: `CORSMiddleware` with both origins             |
| 2  | Two routers are mounted: `/watch-queries` and scrapes (no prefix)                   | VERIFIED   | `backend/main.py` lines 39-40: `include_router(watch_queries_router)`, `include_router(scrapes_router)` |
| 3  | POST /watch-queries/ creates a watch query and returns 201 with full response       | VERIFIED   | `watch_queries.py` line 29: `status_code=201`; test_create_watch_query passes |
| 4  | URL deduplication silently removes duplicates at create and update time (QUERY-05)  | VERIFIED   | `list(dict.fromkeys(payload.urls))` in POST handler (line 32) and PATCH handler (line 104) |
| 5  | User can list all watch queries via GET /watch-queries/                             | VERIFIED   | `@router.get("/", response_model=list[WatchQueryResponse])` line 42; test_list_watch_queries passes |
| 6  | User can get a single query with embedded latest scrape results via GET /watch-queries/{id} | VERIFIED | GET detail builds `RetailerUrlWithLatest` with `latest_result`; test_get_watch_query passes |
| 7  | User can update a watch query via PATCH /watch-queries/{id} with diff-based URL replacement | VERIFIED | PATCH handler lines 91-123; test_update_watch_query and test_update_watch_query_urls_with_dedup pass |
| 8  | User can delete via DELETE /watch-queries/{id} and get 204                          | VERIFIED   | `@router.delete("/{query_id}", status_code=204)` line 126; test_delete_watch_query passes |
| 9  | User can pause and resume a watch query by patching is_active                       | VERIFIED   | PATCH endpoint accepts `is_active` bool; test_pause_resume_watch_query passes |
| 10 | User can trigger an on-demand scrape via POST /watch-queries/{id}/scrape            | VERIFIED   | `@router.post("/watch-queries/{query_id}/scrape")` in scrapes.py line 33; test_trigger_scrape passes with direction="new", delta_cents=0 |
| 11 | User can view price history via GET /retailer-urls/{id}/history ordered newest-first | VERIFIED  | GET history in scrapes.py lines 91-140; test_get_history passes with correct direction/delta assertions |
| 12 | BrowserManager is lazily initialized on first scrape request                        | VERIFIED   | Module-level `_browser_manager: BrowserManager | None = None`; `get_browser_manager()` factory initializes on first call |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact                                         | Expected                                     | Status     | Details                                                     |
|--------------------------------------------------|----------------------------------------------|------------|-------------------------------------------------------------|
| `backend/app/api/__init__.py`                    | API package init                             | VERIFIED   | File exists (empty init)                                    |
| `backend/app/api/watch_queries.py`               | Complete CRUD router                         | VERIFIED   | 132 lines; POST, GET list, GET detail, PATCH, DELETE        |
| `backend/app/api/scrapes.py`                     | Scrape trigger and history endpoints         | VERIFIED   | 141 lines; lazy BrowserManager, POST /scrape, GET /history  |
| `backend/main.py`                                | CORS middleware and router mounting          | VERIFIED   | CORSMiddleware with both origins; both routers mounted       |
| `backend/app/schemas/watch_query.py`             | LatestScrapeResult, RetailerUrlWithLatest, WatchQueryDetailResponse | VERIFIED | All three schemas present (lines 70-101) |
| `backend/app/schemas/scrape.py`                  | ScrapeResultResponse, ScrapeJobResponse, HistoryRecordResponse | VERIFIED | All three schemas present, 44 lines total |
| `backend/app/services/scrape_service.py`         | calculate_price_delta with optional previous_price_cents | VERIFIED | `previous_price_cents: int | None = None` at line 116 |
| `backend/tests/api/conftest.py`                  | Async test client fixture with DB override   | VERIFIED   | ASGITransport + AsyncClient + `app.dependency_overrides[get_db]` |
| `backend/tests/api/test_watch_queries.py`        | Full CRUD test coverage (12 tests)           | VERIFIED   | 12 tests, all active (no skips), all pass                   |
| `backend/tests/api/test_scrapes.py`              | Scrape trigger and history tests             | VERIFIED   | 4 tests with mocked BrowserManager, all pass                |

---

### Key Link Verification

| From                                      | To                                            | Via                                               | Status  | Details                                                                     |
|-------------------------------------------|-----------------------------------------------|---------------------------------------------------|---------|-----------------------------------------------------------------------------|
| `backend/main.py`                         | `backend/app/api/watch_queries.py`            | `app.include_router(watch_queries_router)`        | WIRED   | Line 39 in main.py; line 10 imports router                                  |
| `backend/main.py`                         | `backend/app/api/scrapes.py`                  | `app.include_router(scrapes_router)`              | WIRED   | Line 40 in main.py; line 11 imports router                                  |
| `backend/main.py`                         | `backend/app/api/scrapes.py`                  | `_browser_manager` cleanup in lifespan           | WIRED   | Lines 23-26: checks `_browser_manager` and calls `stop()`                   |
| `backend/tests/api/conftest.py`           | `backend/main.py`                             | `ASGITransport(app=app)`                          | WIRED   | Line 33: `transport = ASGITransport(app=app)`                               |
| `backend/app/api/watch_queries.py`        | `backend/app/repositories/watch_query.py`     | `get_watch_query, list_watch_queries, update_watch_query, delete_watch_query` | WIRED | All four functions imported and used in route handlers |
| `backend/app/api/watch_queries.py`        | `backend/app/repositories/scrape_result.py`   | `get_latest_scrape_result` for embedded results   | WIRED   | Line 8 import; used in GET detail handler line 59                           |
| `backend/app/api/scrapes.py`              | `backend/app/services/scrape_service.py`      | `run_scrape_job(session, watch_query_id, browser_manager)` | WIRED | Line 16 import; called at line 41 in trigger_scrape handler |
| `backend/app/api/scrapes.py`              | `backend/app/services/scrape_service.py`      | `calculate_price_delta` for history deltas        | WIRED   | Line 16 import; called in both trigger_scrape (line 63) and get_history (line 118) |
| `backend/app/api/scrapes.py`              | `backend/app/scrapers/browser.py`             | Lazy singleton `get_browser_manager()`            | WIRED   | `_browser_manager` module variable lines 21-30; called in trigger_scrape line 40 |
| `backend/app/api/scrapes.py`              | `backend/app/repositories/scrape_result.py`   | ScrapeResult query for history records            | WIRED   | Line 8 import `ScrapeResult`; used in select statement line 98              |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                              | Status    | Evidence                                                                 |
|-------------|-------------|--------------------------------------------------------------------------|-----------|--------------------------------------------------------------------------|
| QUERY-01    | 03-01       | User can create a watch query with search term, retailer URLs, threshold  | SATISFIED | POST /watch-queries/ returns 201; test_create_watch_query passes          |
| QUERY-02    | 03-02       | User can edit a watch query's name, threshold, and retailer URLs          | SATISFIED | PATCH /watch-queries/{id} updates scalar fields; test_update_watch_query passes |
| QUERY-03    | 03-02       | User can delete a watch query                                             | SATISFIED | DELETE /watch-queries/{id} returns 204; test_delete_watch_query passes    |
| QUERY-04    | 03-02       | User can pause and resume a watch query                                   | SATISFIED | PATCH is_active toggles; test_pause_resume_watch_query passes             |
| QUERY-05    | 03-01, 03-02| System deduplicates retailer URLs at create and edit time                 | SATISFIED | `list(dict.fromkeys())` in both POST and PATCH handlers; dedup tests pass |
| SCRAPE-03   | 03-03       | User can trigger an on-demand scrape from the UI                          | SATISFIED | POST /watch-queries/{id}/scrape returns results; test_trigger_scrape passes |

**All 6 phase-3 requirements satisfied. No orphaned requirements.**

---

### Anti-Patterns Found

None. Scan across all modified files found:
- No TODO/FIXME/HACK/PLACEHOLDER comments
- No stub return values (empty list, empty dict without logic)
- No `session.commit()` or `db.commit()` calls in route handlers (transaction handled entirely by `get_db` dependency)
- No skipped tests in the final file state (`pytest.mark.skip` removed for all implemented tests)

---

### Human Verification Required

None. All phase-3 deliverables are backend API endpoints and tests verifiable programmatically. The 90-test suite passes cleanly, covering all CRUD operations, scrape triggering, price history retrieval, 404 handling, and validation rejection (422).

---

## Verification Summary

Phase 3 goal is fully achieved. The FastAPI layer implements all six required capabilities:

- **QUERY-01/05**: POST /watch-queries/ creates queries with URL deduplication on creation.
- **QUERY-02/05**: PATCH /watch-queries/{id} updates scalar fields and replaces URLs with diff-based deduplication, preserving scrape history for retained URLs.
- **QUERY-03**: DELETE /watch-queries/{id} returns 204 and cascades cleanup.
- **QUERY-04**: PATCH is_active toggles pause/resume; paused queries retain config.
- **SCRAPE-03**: POST /watch-queries/{id}/scrape triggers a synchronous on-demand scrape with mocked or real BrowserManager.

Bonus capability (not a separate requirement but part of the phase): GET /retailer-urls/{id}/history returns price history newest-first with consecutive-pair delta computation via the extended `calculate_price_delta()`.

All 7 commits (03ef3bb, 3a6157c, 9848bf6, d45fd13, dc8fb74, a8b1910, c3f2894) confirmed in git log. Full test suite: 90 passed, 0 failed, 0 skipped.

---

_Verified: 2026-03-18_
_Verifier: Claude (gsd-verifier)_
