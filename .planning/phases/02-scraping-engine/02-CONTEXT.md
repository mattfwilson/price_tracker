# Phase 2: Scraping Engine - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

A Playwright-based scraping service that fetches retailer pages, extracts product data (name, price, listing URL, retailer name), persists immutable scrape records, handles failures with retry logic, and is validated via a standalone CLI script. No API or frontend in this phase. Scheduling (APScheduler) is Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Anti-detection strategy
- Use **patchright** (drop-in async Playwright replacement with built-in stealth patches) — not bare Playwright or playwright-stealth plugin
- **Persistent browser context** — one browser process kept alive, pages opened and closed per scrape. Restarted on error.
- Run **headless** always — no configurable headed mode needed
- Add **minimal human-simulation**: random delay (0.5–2s) between page navigations only. No mouse movement simulation.

### Extraction architecture
- **Site-specific extractor classes** — abstract `BaseExtractor` with `extract(url) -> ScrapeData`. Each retailer subclass implements its own CSS selectors and parsing logic.
- Module lives in `backend/app/scrapers/` (separate from `services/`)
- **Phase 2 implements extractors for 5 retailers:** Amazon, Best Buy, Walmart, Newegg, Microcenter
- Extracted data matches exactly what the `ScrapeResult` model needs: `product_name`, `price_cents`, `listing_url`, `retailer_name` — no extra fields

### Failure classification & retry policy
- **Three-tier failure classification:**
  - `NETWORK_ERROR` — timeout, connection refused — retryable
  - `EXTRACTION_ERROR` — price not found, parse failure — retryable with limit
  - `BLOCKED` — bot detection, CAPTCHA, 403 response — hard fail immediately, no retry
- Stored in `ScrapeJob.error_message` with enum prefix (e.g., `NETWORK_ERROR: connection timeout`)
- **Retry policy:** 3 retries with exponential backoff — wait 2s, 4s, 8s between attempts
- **Partial job success:** If some retailer URLs succeed and others fail within a job, `ScrapeJob.status = 'partial_success'`. Successful results are stored; failed URLs logged per-result.

### CLI validation script
- Located at `backend/scripts/scrape.py`
- Accepts **one or more URLs as positional arguments**: `python scripts/scrape.py URL1 URL2 ...`
- **Print only** — no database writes. Validates extraction pipeline, not storage.
- Output: structured per-URL block showing Retailer, Product, Price (human + cents), Listing URL, or ERROR with type and message
- Example output format:
  ```
  URL: https://amazon.com/dp/B0...
    Retailer:  Amazon
    Product:   Sony WH-1000XM5 Headphones
    Price:     $279.99 (27999 cents)
    Listing:   https://amazon.com/dp/B0...

  URL: https://bestbuy.com/...
    ERROR [EXTRACTION_ERROR]: price element not found
  ```

### Claude's Discretion
- Exact CSS selectors per retailer (validated against live pages during implementation — STATE.md noted these may be stale)
- Browser context configuration details (viewport, user agent string, locale)
- Jitter range for the random delay (within the 0.5–2s guideline)
- How the `BaseExtractor` determines which subclass handles a given URL (domain matching)
- `tenacity` vs manual retry loop for backoff implementation

</decisions>

<canonical_refs>
## Canonical References

No external specs — requirements are fully captured in decisions above and project-level files.

### Project constraints
- `.planning/PROJECT.md` — Stack constraints (Playwright, FastAPI, SQLite, APScheduler), key decisions rationale
- `.planning/REQUIREMENTS.md` — SCRAPE-01 (extraction fields), SCRAPE-04 (2-3x retry with exponential backoff), HIST-01 (prices as integer cents), HIST-02 (delta calculation)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/models/scrape_result.py` — `ScrapeResult` model with all fields the extractor must populate: `product_name`, `price_cents`, `listing_url`, `retailer_name`, `retailer_url_id`, `scrape_job_id`
- `backend/app/models/scrape_job.py` — `ScrapeJob` model: `status`, `started_at`, `completed_at`, `error_message` — the scraping service writes to this
- `backend/app/models/watch_query.py` — `WatchQuery.retailer_urls` relationship used to get URLs to scrape
- `backend/app/core/database.py` — `async_session_factory` for creating DB sessions in non-FastAPI contexts (CLI script, background service)
- `backend/app/core/config.py` — `settings` singleton for config (database path, debug flag)

### Established Patterns
- Async throughout — all service and repository functions use `AsyncSession`
- SQLAlchemy 2.0 `mapped_column()` / `Mapped[T]` style — new models follow this
- Repository layer in `backend/app/repositories/` — scrape result persistence follows same pattern
- `flush()` not `commit()` in repositories — session commit handled by caller

### Integration Points
- Phase 3 (API) will call the scraping service from a FastAPI endpoint — service must be importable and async-compatible
- Phase 4 (Scheduling) will call the same service from APScheduler jobs — same async interface
- `ScrapeResult` records are read by Phase 5 (frontend) and Phase 6 (history charts)

</code_context>

<specifics>
## Specific Ideas

- Five specific retailers for Phase 2: Amazon, Best Buy, Walmart, Newegg, Microcenter — all five need working extractors before Phase 2 is complete
- STATE.md note: retailer CSS selectors may be stale by implementation time — validate against live pages during Phase 2 development, not just design

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-scraping-engine*
*Context gathered: 2026-03-18*
