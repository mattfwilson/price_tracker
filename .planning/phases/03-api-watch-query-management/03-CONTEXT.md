# Phase 3: API + Watch Query Management - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

FastAPI REST endpoints that expose watch query CRUD and on-demand scrape triggering. The scraping engine (Phase 2) is complete and ready to consume. This phase does NOT include scheduling (Phase 4), alert evaluation (Phase 4), or frontend (Phase 5). It delivers the full CRUD surface plus the API endpoints the frontend will call to manage queries and trigger scrapes.

</domain>

<decisions>
## Implementation Decisions

### On-demand scrape behavior
- Synchronous — POST /watch-queries/{id}/scrape awaits run_scrape_job() and returns the completed results in one response
- HTTP 200 on success (not 202 — the response contains the data, not just acceptance)
- Returns full result set: all ScrapeResult records for the job with product name, price_cents, retailer name, listing URL, and price delta vs previous
- BrowserManager initializes lazily on first scrape request (not in lifespan startup); subsequent requests reuse the shared instance

### Scrape results and history endpoints
- GET /watch-queries/{id} returns watch query config AND the latest scrape result embedded per retailer URL (product_name, price_cents, listing_url, scraped_at, price delta direction)
- Price history endpoint built in Phase 3: GET /retailer-urls/{id}/history — returns all scrape results for a URL ordered newest-first
- History records include computed delta fields (direction, delta_cents, pct_change) server-side via calculate_price_delta() — frontend receives ready-to-display data

### Duplicate URL handling
- Silent deduplication — exact string match (byte-for-byte), no normalization
- Duplicates are removed before writing; response returns the cleaned, canonical URL list
- No error or warning flag in the response — caller sees the deduplicated result as if they sent it clean
- Applied at both create and edit time (per QUERY-05)

### Router and CORS structure
- Split routers in backend/app/api/: watch_queries.py (CRUD: GET, POST, PATCH, DELETE) and scrapes.py (POST scrape trigger + GET history endpoints)
- CORS locked to http://localhost:5173 (Vite dev) and http://localhost:3000 (fallback) — not wide-open wildcard
- Routers mounted in backend/main.py with appropriate prefixes

### Claude's Discretion
- Exact BrowserManager singleton implementation (module-level instance vs app.state vs DI)
- Pydantic response schema for the embedded latest_result on retailer URLs (extend RetailerUrlResponse or separate schema)
- Pagination on history endpoint (or not, given small personal dataset)
- Error response format for 404 and validation errors (FastAPI defaults are fine)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project constraints
- `.planning/PROJECT.md` — Stack constraints (FastAPI, SQLite, SQLAlchemy, APScheduler, Playwright), key decisions rationale
- `.planning/REQUIREMENTS.md` — QUERY-01 through QUERY-05 (watch query CRUD and dedup), SCRAPE-03 (on-demand scrape trigger)

### Prior phase context
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — Session/DI pattern (Depends(get_db)), SQLAlchemy async patterns, flush() vs commit() discipline
- `.planning/phases/02-scraping-engine/02-CONTEXT.md` — BrowserManager (persistent context, lazy restart on error), run_scrape_job() interface, failure classification

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/schemas/watch_query.py` — WatchQueryCreate, WatchQueryUpdate, WatchQueryResponse, RetailerUrlResponse already defined; RetailerUrlResponse will need a latest_result field added
- `backend/app/repositories/watch_query.py` — create_watch_query, get_watch_query, list_watch_queries, update_watch_query, delete_watch_query — all implemented and tested
- `backend/app/repositories/scrape_result.py` — get_latest_scrape_result() for embedding latest price; create_scrape_result() and create_scrape_job() for the scrape endpoint
- `backend/app/services/scrape_service.py` — run_scrape_job(session, watch_query_id, browser_manager) orchestrates full scrape; calculate_price_delta() computes delta vs previous
- `backend/app/scrapers/browser.py` — BrowserManager (persistent patchright context, headless, async)
- `backend/app/core/database.py` — async_session_factory for non-FastAPI contexts; get_db dependency for routes
- `backend/main.py` — FastAPI app with lifespan + /health endpoint; ready for router mounting and CORS middleware

### Established Patterns
- Async throughout — all repository and service functions are async with AsyncSession
- SQLAlchemy 2.0 mapped_column() / Mapped[T] style — new schemas and repositories follow this
- Repository discipline: flush() not commit() inside repo functions; session commit owned by the route handler (via DI)
- Dependency injection: `db: AsyncSession = Depends(get_db)` in all route handlers

### Integration Points
- Phase 4 (Scheduling) will call run_scrape_job() from APScheduler jobs using the same async interface — do not change the signature
- Phase 5 (Dashboard Frontend) consumes all CRUD and results endpoints built here
- Phase 6 (Price History) consumes the history endpoint built in 03-03

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

*Phase: 03-api-watch-query-management*
*Context gathered: 2026-03-18*
