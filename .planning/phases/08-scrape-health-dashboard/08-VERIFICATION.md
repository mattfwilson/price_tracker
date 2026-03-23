---
phase: 08-scrape-health-dashboard
verified: 2026-03-23T11:27:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 08: Scrape Health Dashboard Verification Report

**Phase Goal:** Build a scrape health dashboard that surfaces per-URL success rates, failure counts, and error types, enabling users to diagnose scraping problems without reading logs.
**Verified:** 2026-03-23T11:27:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every scrape attempt (success or failure) creates a row in scrape_url_attempts | VERIFIED | `scrape_service.py` calls `create_scrape_url_attempt` in both `except ScrapeError as e` (line 138) and `except Exception as e` (line 149) clauses, plus `is_success=True` on the success path (line 130) |
| 2 | Health stats (success rate, consecutive failures, last error) are computed correctly from the last 10 attempts per URL | VERIFIED | `get_health_stats_for_all_urls` uses `row_number() OVER (PARTITION BY retailer_url_id ORDER BY scraped_at DESC)` with `WHERE rn <= 10`; consecutive failures computed via `_compute_consecutive_failures`; 18 backend tests pass |
| 3 | URLs are categorized as healthy (>=80%), degraded (50-79%), or failing (<50%) based on success rate | VERIFIED | `scrape_url_attempt.py` repository: `if success_rate >= 0.8: status = "healthy"` / `elif success_rate >= 0.5: status = "degraded"` / `else: status = "failing"` |
| 4 | GET /scrape-health/urls returns all retailer URLs with computed health stats | VERIFIED | `backend/app/api/health.py` router with `@router.get("/urls")` registered in `main.py` at line 50; 18 backend tests pass including API tests |
| 5 | User can navigate to /health via a nav link in the header | VERIFIED | `Header.tsx` imports `NavLink` from react-router-dom and renders `to="/health"` with text "Health"; `App.tsx` has `path="/health"` route |
| 6 | Health page lists every retailer URL with status dot, domain, query name, success rate, last success, consecutive failures, and last error | VERIFIED | `HealthTable.tsx` renders all 7 columns: Status (HealthStatusDot), URL (domain), Watch Query, Rate (success_count/window_size), Last Success (formatRelativeTime or "--"), Fails, Last Error; 10 frontend tests pass |
| 7 | URLs are color-coded as healthy (green), degraded (yellow), or failing (red) | VERIFIED | `HealthStatusDot.tsx`: healthy=`bg-emerald-500`, degraded=`bg-amber-500`, failing=`bg-red-500`; verified by 3 HealthStatusDot tests |
| 8 | User can sort the table by status, watch query name, and last success date | VERIFIED | `HealthTable.tsx`: STATUS_ORDER map (failing=2/degraded=1/healthy=0) with desc default; `localeCompare` for query; date comparison with null-last logic; 3 sort tests pass |
| 9 | User can filter to show only degraded and failing URLs | VERIFIED | `HealthFilter.tsx` exports "All" / "Degraded & Failing" toggle; `HealthPage.tsx` applies `u.status !== "healthy"` filter when mode is "problems"; 2 filter tests pass |
| 10 | Each QueryCard displays per-URL mini-dots below the status line showing health status | VERIFIED | `QueryCard.tsx` renders `<UrlHealthDots healthData={healthData} />` after StatusDot div (line 182); prop threaded from DashboardPage through QueryCardGrid |
| 11 | Health data is fetched once at the dashboard level, not per-card (no N+1) | VERIFIED | `DashboardPage.tsx` calls `useHealthUrls()` once, builds `healthByQuery` useMemo map, passes to QueryCardGrid; `QueryCard.tsx` does NOT import `useHealthByQuery`; 9 UrlHealthDots tests pass |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/scrape_url_attempt.py` | ScrapeUrlAttempt SQLAlchemy model | VERIFIED | Contains `class ScrapeUrlAttempt(Base)`, `__tablename__ = "scrape_url_attempts"`, `retailer_url_id` ForeignKey, `scraped_at`, `is_success`, `error_type`, `error_message` |
| `backend/alembic/versions/b5e1f3a8c7d9_add_scrape_url_attempts.py` | Alembic migration for scrape_url_attempts table | VERIFIED | `op.create_table('scrape_url_attempts')`, `down_revision = 'a3b7c9d1e4f2'`, composite index `ix_scrape_url_attempts_url_time` on `(retailer_url_id, scraped_at DESC)` |
| `backend/app/repositories/scrape_url_attempt.py` | Attempt CRUD + health stat queries | VERIFIED | Exports `create_scrape_url_attempt` and `get_health_stats_for_all_urls` with SQL window functions; 18 tests green |
| `backend/app/schemas/health.py` | Pydantic response schemas for health API | VERIFIED | `class UrlHealthResponse(BaseModel)` with all 11 fields; `class HealthListResponse` |
| `backend/app/api/health.py` | GET /scrape-health/urls endpoint | VERIFIED | `router = APIRouter(prefix="/scrape-health")`, `@router.get("/urls")`, `@router.get("/query/{watch_query_id}")` |
| `frontend/src/hooks/use-health.ts` | TanStack Query hook for health data | VERIFIED | Exports `useHealthUrls()` and `useHealthByQuery()`; wired to `api.scrapeHealth.urls` |
| `frontend/src/components/health/HealthStatusDot.tsx` | Reusable health dot component | VERIFIED | `export function HealthStatusDot` with healthy/degraded/failing color map |
| `frontend/src/components/health/HealthFilter.tsx` | Filter bar for All / Degraded & Failing | VERIFIED | `export function HealthFilter` with both buttons including "Degraded & Failing" |
| `frontend/src/components/health/HealthTable.tsx` | Sortable health table | VERIFIED | `export function HealthTable` with 3-column sort, STATUS_ORDER, ArrowUp/ArrowDown icons |
| `frontend/src/pages/HealthPage.tsx` | Health page at /health route | VERIFIED | `export function HealthPage`, uses `useHealthUrls()`, title "Scrape Health", empty state "No URLs tracked", filter wiring |
| `frontend/src/components/dashboard/UrlHealthDots.tsx` | Mini-dot row component for QueryCard | VERIFIED | `export function UrlHealthDots`, uses HealthStatusDot size="sm", title tooltip, domain label, returns null for empty |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scrape_service.py` | `scrape_url_attempt.py` (repo) | `create_scrape_url_attempt` called per-URL | WIRED | Import on line 21; called with `is_success=True` (line 130), `is_success=False` in both except clauses (lines 139, 150) |
| `backend/app/api/health.py` | `scrape_url_attempt.py` (repo) | `get_health_stats_for_all_urls` in GET handler | WIRED | Imported and called directly in both `/urls` and `/query/{id}` handlers |
| `backend/main.py` | `backend/app/api/health.py` | `app.include_router(health_router)` | WIRED | Line 10 import, line 50 `include_router`; existing `@app.get("/health")` at line 61 is preserved with no collision |
| `HealthPage.tsx` | `use-health.ts` | `useHealthUrls()` hook | WIRED | Imported and called in HealthPage function body |
| `use-health.ts` | `/scrape-health/urls` | `api.scrapeHealth.urls` apiFetch call | WIRED | `api.ts` line 91: `apiFetch<HealthListResponse>("/scrape-health/urls")` |
| `App.tsx` | `HealthPage.tsx` | `Route element` | WIRED | `path="/health"` route with `element={<HealthPage />}` |
| `Header.tsx` | `/health` | NavLink | WIRED | `NavLink to="/health"` with isActive styling |
| `QueryCard.tsx` | `UrlHealthDots.tsx` | `<UrlHealthDots` rendered after StatusDot | WIRED | `<UrlHealthDots healthData={healthData} />` at line 182; `StatusDot` preserved at line 173 |
| `DashboardPage.tsx` | `use-health.ts` | `useHealthUrls()` called once at dashboard level | WIRED | Line 16: `const { data: allHealthData } = useHealthUrls()` |
| `DashboardPage.tsx` | `QueryCard.tsx` (via QueryCardGrid) | `healthByQuery` prop filtered by watch_query_id | WIRED | `healthByQuery` useMemo at line 26; passed as `healthByQuery={healthByQuery}` to QueryCardGrid at line 81; QueryCardGrid threads to each QueryCard |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| HEALTH-01 | 08-01, 08-02 | User can view health dashboard page with per-URL success rate, last successful scrape, consecutive failures, and last error type | SATISFIED | HealthPage renders HealthTable showing all columns; backend computes stats from scrape_url_attempts table |
| HEALTH-02 | 08-01, 08-02 | URLs visually categorized as healthy (green), degraded (yellow), or failing (red) | SATISFIED | HealthStatusDot maps `bg-emerald-500` / `bg-amber-500` / `bg-red-500`; backend computes status with >=80%/>=50%/<50% thresholds |
| HEALTH-03 | 08-02 | User can sort and filter health URL list by status, watch query, and last success date | SATISFIED | HealthTable: sort by status (failing-first default), watch query (alpha), last success (nulls-last); HealthFilter: All / Degraded & Failing toggle |
| HEALTH-04 | 08-03 | Dashboard query cards show health status indicator for each URL at a glance | SATISFIED | UrlHealthDots component renders per-URL mini-dots in QueryCard; domain labels; tooltip with success rate and last success time |

No orphaned requirements found. All four HEALTH-0x IDs declared across plans are covered.

---

### Anti-Patterns Found

No blockers or warnings. Two `return null` instances examined:

1. `HealthTable.tsx` line 71 — `SortIcon` helper returns null when a column is not the active sort column. This is correct conditional rendering, not a stub.
2. `UrlHealthDots.tsx` line 10 — Returns null when `healthData` is empty or undefined. This is correct guard behavior per the plan spec ("When health data is empty or loading, UrlHealthDots renders nothing").

No TODOs, FIXMEs, placeholder text, hardcoded empty arrays being rendered as final output, or unimplemented handler bodies found in any phase-08 artifact.

---

### Human Verification Required

The following behaviors cannot be verified programmatically:

#### 1. Tooltip hover display

**Test:** Navigate to `/` in a browser, hover over a mini-dot in a QueryCard that has health data.
**Expected:** Native browser tooltip appears showing format `"{domain} · {success}/{window} · last success {relative_time}"`.
**Why human:** `title` attribute tooltip rendering is browser-native and not testable via jsdom.

#### 2. NavLink active state

**Test:** Navigate to `/health` in a browser, inspect the "Health" nav link.
**Expected:** "Health" nav text renders in `text-foreground` color (darker), not `text-muted-foreground`.
**Why human:** CSS class application and computed color rendering requires a real browser.

#### 3. Health page end-to-end with real data

**Test:** Trigger a scrape that produces some failures, then navigate to `/health`.
**Expected:** Failing URLs appear at top of the table (failing-first sort), colored red, with correct error type displayed.
**Why human:** Requires live backend with recorded scrape attempts; integration behavior beyond unit tests.

---

## Summary

Phase 08 goal is fully achieved. All 11 observable truths are verified against the actual codebase:

- The backend data pipeline is complete: `ScrapeUrlAttempt` model and migration exist, every scrape attempt is recorded in the service loop via separate `ScrapeError` and generic `Exception` clauses, and health stats are computed via SQL window functions with correct status thresholds.
- The health API endpoints (`GET /scrape-health/urls` and `GET /scrape-health/query/{id}`) are registered and wired. The existing `GET /health` server check at line 61 of `main.py` is unaffected.
- The frontend Health page at `/health` is complete with a sortable (status/query/lastSuccess), filterable (All/Degraded & Failing) table, status dots in semantic colors, and empty/loading/error states.
- QueryCards on the dashboard display per-URL mini-dots via `UrlHealthDots`. Health data is fetched once at `DashboardPage` level and distributed through `QueryCardGrid` — no N+1 requests. The existing `StatusDot` is preserved.
- All backend health tests pass (18/18). All frontend health tests pass (19/19, covering HealthTable, HealthFilter, HealthStatusDot, and UrlHealthDots).
- All four requirement IDs (HEALTH-01 through HEALTH-04) are satisfied with direct implementation evidence.

Three items are flagged for human verification: tooltip rendering, NavLink active state, and end-to-end behavior with live scrape data. These are visual/interactive behaviors that tests cannot cover.

---

_Verified: 2026-03-23T11:27:00Z_
_Verifier: Claude (gsd-verifier)_
