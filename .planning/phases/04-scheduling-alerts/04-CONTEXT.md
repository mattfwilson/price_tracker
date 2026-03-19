# Phase 4: Scheduling + Alerts - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

APScheduler background jobs that run scrapes automatically on per-query schedules, alert evaluation that fires when scraped prices hit the configured threshold, and SSE push to connected browser clients for real-time notification. This phase does NOT include frontend UI (Phase 5) — it delivers the backend loop: schedule → scrape → evaluate → alert → push.

</domain>

<decisions>
## Implementation Decisions

### Repeat alert behavior
- Alert fires only on **first breach** — when price drops to/below threshold for the first time (per retailer URL)
- No repeat alert while price stays at or below threshold across subsequent scrapes
- A **new alert fires on re-breach**: if price rises above threshold and then drops back below, that is treated as a new breach and fires a new alert
- Implementation: before creating an alert, check if the most recent alert for this retailer URL is still "active" (i.e., the last scrape result for that URL was already below threshold); if so, skip

### Alert granularity
- **One alert record per scrape result that breaches threshold** — not one per job
- If a scrape job finds 3 retailer URLs below threshold, 3 separate Alert records are created (each linked to its ScrapeResult via scrape_result_id)
- Rationale: alert log shows retailer-specific detail ("Amazon $85", "Walmart $82" as distinct rows)

### Scheduler startup and recovery
- **Skip missed scrapes** — if a scrape was due while the app was offline, do not run it immediately on startup; wait for the next scheduled interval
- **Auto-register on startup**: during FastAPI lifespan startup, scheduler reads all non-paused watch queries from the DB and registers their APScheduler jobs (using `misfire_grace_time` to skip missed fires rather than run them)
- Job IDs keyed by watch_query_id so they can be cancelled/updated when a query is paused, resumed, edited, or deleted via API

### SSE event scope
- SSE stream pushes **alert events only** — no scrape job status events
- Scrape job status (running/finished) is available via polling the existing API endpoints in Phase 5
- **Full detail payload per alert event:**
  - `alert_id`, `watch_query_id`, `watch_query_name`
  - `product_name`, `price_cents`, `retailer_name`, `listing_url`
  - `created_at` (timestamp)
  - `unread_count` (total unread alerts at time of push)
- Frontend can render the toast and update badge count from this payload without a follow-up API call

### Claude's Discretion
- APScheduler job store (MemoryJobStore vs SQLAlchemyJobStore) — MemoryJobStore is fine since jobs are always rebuilt from DB on startup
- Exact APScheduler scheduler type (AsyncIOScheduler vs BackgroundScheduler with asyncio bridge)
- SSE connection management implementation (asyncio.Queue per client, generator pattern)
- Alert evaluation: inline within run_scrape_job (after each result is stored) or as a post-job pass — either is fine
- Exact re-breach detection query structure

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — SCRAPE-02 (schedule intervals: 6h, 12h, daily, weekly), ALERT-01 (fires at or below threshold), ALERT-02 (badge + toast via SSE), ALERT-03 (alert log view), ALERT-04 (mark read / dismiss all)
- `.planning/PROJECT.md` — APScheduler constraint (embedded, no broker); stack constraints (FastAPI, SQLite, async)

### Prior phase context
- `.planning/phases/03-api-watch-query-management/03-CONTEXT.md` — run_scrape_job() interface (must not change), BrowserManager lazy singleton, lifespan structure, async patterns
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — async_session_factory for non-FastAPI contexts (scheduler jobs need this to get DB sessions), SQLAlchemy async patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/models/alert.py` — Alert model exists: id, scrape_result_id, watch_query_id, is_read, created_at; relationship to ScrapeResult and WatchQuery already defined
- `backend/app/services/scrape_service.py` — run_scrape_job(session, watch_query_id, browser_manager) — scheduler jobs call this directly; do not change signature
- `backend/app/core/database.py` — async_session_factory for creating sessions outside FastAPI request context (scheduler jobs use this)
- `backend/main.py` — FastAPI lifespan already handles BrowserManager shutdown; scheduler startup/shutdown integrates here

### Established Patterns
- Async throughout — APScheduler jobs must use AsyncIOScheduler with asyncio event loop, or create their own async sessions via async_session_factory
- Repository discipline: flush() not commit() inside repo functions; caller owns the session commit — alert evaluation service follows this pattern
- Job management: watch_query_id as APScheduler job ID string (e.g., f"scrape_query_{watch_query_id}") for easy cancel/add operations

### Integration Points
- API endpoints for pause/resume/delete/edit (Phase 3) must notify the scheduler to cancel/re-add jobs — scheduler needs a singleton accessible from route handlers
- Phase 5 (Dashboard Frontend) connects to the SSE endpoint for badge count and toast notifications
- Phase 5 polls existing Phase 3 endpoints for scrape job status (not SSE)

</code_context>

<specifics>
## Specific Ideas

- No specific requirements — open to standard approaches for things under Claude's discretion

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-scheduling-alerts*
*Context gathered: 2026-03-18*
