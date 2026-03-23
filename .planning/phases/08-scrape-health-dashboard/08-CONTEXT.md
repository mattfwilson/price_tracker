# Phase 8: Scrape Health Dashboard - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Per-URL scrape health tracking — a dedicated `/health` page listing every retailer URL with its success rate, consecutive failures, last error, and health status (healthy/degraded/failing). QueryCards gain per-URL health mini-dots inline. Health data is stored in a new `scrape_url_attempts` table populated on every scrape attempt.

No in-page actions (Scrape Now, Remove URL) — the health page is read-only observability. To act on a failing URL, users navigate to the watch query and edit it.

</domain>

<decisions>
## Implementation Decisions

### Data Model: Per-URL Attempt Tracking
- **D-01:** Add a new `scrape_url_attempts` table — one row per URL per scrape attempt: `retailer_url_id`, `scraped_at`, `is_success` (bool), `error_type` (string), `error_message` (text, nullable). Requires Alembic migration.
- **D-02:** Error type stored as a freeform string (exception class name or scraper failure label) — not an enum. Flexible when new error types emerge. Claude picks the appropriate convention based on existing `BaseExtractor` failure patterns.
- **D-03:** Scrape service must write a row to `scrape_url_attempts` for every URL on every attempt (both success and failure).

### Health Thresholds
- **D-04:** Window = **last 10 attempts** per URL (not calendar-based).
- **D-05:** Status categories:
  - **Healthy (green):** ≥ 80% success rate (8+ of last 10)
  - **Degraded (yellow):** 50–79% success rate
  - **Failing (red):** < 50% success rate (fewer than 5 of last 10)
- **D-06:** URLs with fewer than 10 attempts use actual count as denominator (no padding with assumed successes).

### Health Page (`/health`)
- **D-07:** New route `/health` with a nav item in the header alongside Alerts.
- **D-08:** Table layout — one row per retailer URL. Columns: status dot, URL (domain), watch query name, success rate (e.g., "8/10"), last successful scrape timestamp, consecutive failure count, last error type.
- **D-09:** Sortable by: status (failing first), watch query name, last success date.
- **D-10:** Filterable to show only degraded or failing URLs (filter control above table).
- **D-11:** Read-only — no inline actions. To fix a URL, navigate to the watch query.

### QueryCard Health Indicators
- **D-12:** Per-URL mini-dots appear below the existing StatusDot line on QueryCard — one dot per retailer URL, colored green/yellow/red based on health status.
- **D-13:** Each dot shows the URL's domain label (e.g., "amazon.com") beside it.
- **D-14:** Tooltip on each dot: `{domain} · {success_count}/{window} · last success {relative_time}`. Implemented with shadcn/ui Tooltip or a title attribute.
- **D-15:** Existing StatusDot (ok/error/warning/running/paused) is preserved — the per-URL dots are additional, not a replacement.

### Claude's Discretion
- Error type string convention (e.g., "blocked", "network_error", "parse_error") — base on existing `BaseExtractor` / `FailureType` patterns in the scraping layer
- Exact Tailwind classes, spacing, and icon choices for the health page table
- Whether to use a separate API endpoint (`GET /health/urls`) or extend the existing watch-queries response — pick the cleaner approach
- Loading skeleton strategy for health page data

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — HEALTH-01 through HEALTH-04

### Project constraints
- `.planning/PROJECT.md` — Stack (FastAPI backend, React frontend, SQLite, local-only)

### Existing data models (read before writing migration)
- `backend/app/models/retailer_url.py` — `RetailerUrl` (id, watch_query_id, url); new `scrape_url_attempts` foreign keys here
- `backend/app/models/scrape_result.py` — `ScrapeResult` stores successful scrapes only; no failure records
- `backend/app/models/scrape_job.py` — `ScrapeJob` stores job-level status + error_message; NOT per-URL

### Existing scraping layer (read before modifying scrape service)
- `backend/app/scrapers/base.py` — `BaseExtractor`, `FailureType` enum — use these for error_type convention
- `backend/app/services/scrape_service.py` — orchestrates per-URL scrapes, where attempt rows must be written

### Existing frontend patterns
- `.planning/phases/05-dashboard-frontend/05-CONTEXT.md` — QueryCard structure, StatusDot component, nav/routing pattern
- `frontend/src/components/dashboard/StatusDot.tsx` — existing ok/error/warning/running/paused states; health dots are additional, not replacing
- `frontend/src/components/dashboard/QueryCard.tsx` — where per-URL mini-dots will be added

### Prior phase context
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — prices as integer cents (not directly relevant to health, but establishes migration pattern)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/dashboard/StatusDot.tsx` — already has green/amber/red color tokens; health dots reuse the same color palette
- `frontend/src/components/shared/EmptyState.tsx` — use for health page when no URLs exist yet
- `frontend/src/components/shared/ErrorState.tsx` — use for health page fetch errors
- `backend/app/scrapers/base.py` — `FailureType` enum drives error_type string values for `scrape_url_attempts`

### Established Patterns
- Alembic migrations in `backend/alembic/versions/` — new table needs a new migration file
- TanStack Query hooks pattern from Phase 5 — add `useHealthData()` hook following same structure
- shadcn/ui `Tooltip` available for mini-dot hover behavior
- Tailwind CSS v4 with dark mode support — health page inherits `.dark` theme

### Integration Points
- `backend/app/services/scrape_service.py` — write `scrape_url_attempts` row per URL in the per-URL scrape loop (both success and failure paths)
- `frontend/src/components/layout/Header.tsx` — add "Health" nav link alongside "Alerts"
- `frontend/src/App.tsx` (or router config) — add `/health` route
- `frontend/src/components/dashboard/QueryCard.tsx` — add per-URL dots section after StatusDot

</code_context>

<specifics>
## Specific Ideas

- Mini-dot mockup confirmed by user:
  ```
  ● OK  2 hours ago
  ● amazon.com
  ● bestbuy.com
  ● walmart.com
  ```
  (colored dots, domain label, tooltips on hover)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-scrape-health-dashboard*
*Context gathered: 2026-03-23*
