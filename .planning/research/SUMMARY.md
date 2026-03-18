# Project Research Summary

**Project:** Price Scraper
**Domain:** Personal price tracking / scraping web application
**Researched:** 2026-03-18
**Confidence:** HIGH

## Executive Summary

This is a single-user personal price tracking tool that monitors retailer product pages, stores historical price data, and alerts when prices drop below user-defined thresholds. The expert approach is a single-process Python monolith: FastAPI (async) serving a REST API and React SPA, APScheduler running in-process for background scraping jobs, SQLite for storage, and Playwright for headless browser automation. This stack is well-validated, eliminates external infrastructure dependencies (no Redis, no Celery, no separate broker), and is appropriate for the single-user, local-machine use case.

The recommended approach centers on a strict layered architecture: routers call services, services orchestrate scrapers, scrapers write to the data layer — with no cross-layer shortcuts. The scraping component is the highest-risk element of the product and must be designed first. Anti-bot systems on major retailers (Amazon, Walmart, Best Buy) are the single biggest threat to the product's core value proposition; a scraper that gets blocked silently is worse than no scraper at all. The data layer must use Alembic migrations and SQLite WAL mode from day one, because schema evolution is certain and SQLite locking issues under concurrent read/write are well-documented.

The key risks are: (1) retailer anti-bot detection silently breaking scrapes — mitigated by stealth mode, per-retailer delay configuration, and a scrape health dashboard from the start; (2) Playwright memory leaks in the long-running process — mitigated by fresh browser contexts per scrape job, resource blocking, and context cleanup in finally blocks; (3) CSS selector breakage when retailers update their DOM — mitigated by a fallback selector hierarchy (JSON-LD first, then semantic attributes, then CSS, then regex) and the `price-parser` library for price text parsing. Building the scraping engine before the frontend means these risks are confronted and resolved before any UI is built around them.

## Key Findings

### Recommended Stack

The entire stack carries HIGH confidence from authoritative sources. The backend is Python 3.12+ / FastAPI 0.135+ (which now has native SSE support, eliminating the need for the third-party `sse-starlette` package), SQLAlchemy 2.0 async with aiosqlite, Alembic for migrations, APScheduler 3.x (not 4.x — v4 is pre-release and API-unstable as of March 2026), and Playwright 1.58+ for browser automation. The frontend is React 19 / TypeScript / Vite 8 / TanStack Query / Tailwind CSS 4 / Recharts. This is a conventional, well-documented combination with no experimental dependencies.

Two critical version constraints: APScheduler must be pinned to 3.x (`<4.0`) — v4 has breaking API changes and is explicitly not production-ready. FastAPI 0.135+ is required for native SSE; older versions require the third-party `sse-starlette` package.

**Core technologies:**
- **Python 3.12+ / FastAPI 0.135+**: Async-native web framework with built-in SSE, Pydantic v2 integration, and excellent developer experience
- **SQLAlchemy 2.0 + aiosqlite + Alembic**: The industry-standard ORM with async SQLite support and proper migration tooling; `expire_on_commit=False` is required for async session correctness
- **APScheduler 3.11+ (AsyncIOScheduler)**: Embedded in-process scheduler, shares the FastAPI event loop, no external broker — pin strictly to `<4.0`
- **Playwright 1.58+ (async API only)**: The only viable approach for JS-rendered retailer pages; sync API must never be used in a FastAPI context
- **React 19 / Vite 8 / TanStack Query 5.90+**: Standard 2026 React stack; TanStack Query is purpose-built for server-state management (prices, alerts) and eliminates manual fetch/useEffect patterns
- **Tailwind CSS 4.2+**: CSS-native config (no `tailwind.config.js`), 5x faster engine; implement dark mode from the start if using Tailwind — retrofitting it is painful
- **Recharts 3.8+**: Declarative, React-native charting for price history line charts

### Expected Features

The feature landscape is well-defined by comparison with existing price trackers (CamelCamelCamel, Keepa, self-hosted tools like PriceGhost and PriceBuddy). The multi-URL-per-watch-query capability (tracking the same product across Amazon, Walmart, Best Buy simultaneously) is the primary differentiator versus existing single-retailer tools.

**Must have (table stakes):**
- Watch query CRUD (create, edit, pause, delete) with URL + price threshold — the data model everything else depends on
- Multiple URLs per watch query — core differentiator; same product across all retailers
- Headless browser scraping with scheduled background execution — the product's entire value proposition
- Scrape failure handling with surfaced error status — silent failures are worse than visible ones
- Append-only scrape result storage with timestamps — required for all history and delta features
- Price delta calculation (up/down/unchanged from previous scrape)
- On-demand "scrape now" trigger per query
- Dashboard with all watch queries, latest prices, last scrape timestamp, scrape status
- Drill-down view per query with price history line chart + table
- Threshold line on chart and visual below-threshold indicators
- Alert system: threshold comparison, in-app notification badge/toast, alert log, mark-read

**Should have (differentiators):**
- Multi-retailer lowest-price comparison highlighted on dashboard (already enabled by multi-URL data model — low additional effort)
- Configurable schedule per query (6h, 12h, daily, weekly)
- Price drop percentage display from historical peak
- Sparkline on dashboard cards (at-a-glance trend without drill-down)
- Dark mode — implement with Tailwind from the start; retrofitting costs more than building it in
- Export price history to CSV

**Defer (v2+):**
- Scrape selector configuration UI — hardcode per-retailer selectors initially, build UI later
- Bulk import via CSV — nice-to-have after single-query flow is polished
- Email/SMS notifications — design alert system with event/webhook pattern now so it can be bolted on later
- Request throttling controls UI — implement throttling logic in code; expose UI controls later
- Browser extension — out of scope; different product

**Explicit anti-features (never build):**
- Multi-user auth — single-user personal tool; adds complexity with zero value
- Price prediction/forecasting — insufficient historical data at personal-tool scale
- Proxy rotation / IP management — over-engineering for personal use; reasonable delays are sufficient

### Architecture Approach

The recommended architecture is a single-process monolith with strict internal layering. FastAPI serves both the REST API and the React SPA static build. APScheduler runs in-process on the same event loop. SQLite in WAL mode is the sole data store. The six-table schema (watch_queries, retailer_urls, scrape_results, alerts, scrape_jobs, app_settings) covers the full domain. Prices are stored as integer cents to avoid floating-point issues — this is a hard requirement, not a preference.

The critical boundary rules are: routers never call scrapers directly (always via services), scrapers never import routers, the scheduler only calls service-layer functions, and the frontend never talks to the scheduler (on-demand scrapes go through REST). SSE (not WebSockets) is the correct choice for real-time notifications — communication is unidirectional (server to client only), SSE auto-reconnects in browsers, and FastAPI 0.135+ has native support. The SSE EventManager is an in-memory asyncio queue that fans out to connected clients when scrapes complete or alerts fire.

**Major components:**
1. **React Frontend** — UI rendering, charts (Recharts), SSE EventSource connection for real-time alerts, TanStack Query for all server state
2. **API Layer (routers/)** — HTTP request handling, Pydantic validation, delegates to Service Layer
3. **Service Layer (services/)** — Business logic: watch query CRUD, alert evaluation, price delta calculation, orchestrates scrapers
4. **Scraping Service (scrapers/)** — Strategy pattern: BaseExtractor + per-retailer implementations (Amazon, BestBuy, Walmart, Generic fallback); shared Playwright browser instance with new context per scrape
5. **Scheduler Layer** — APScheduler AsyncIOScheduler lifecycle in FastAPI lifespan; job registration/removal synced to watch query CRUD; restores jobs from DB on startup
6. **SSE Event Manager (events/manager.py)** — In-memory asyncio queue, pub/sub between scraping service and connected browser clients
7. **Data Layer (models/, repositories/)** — SQLAlchemy 2.0 async ORM, Alembic migrations, WAL mode pragmas on connection

### Critical Pitfalls

1. **Retailer anti-bot detection silently breaks all scrapes** — Use `playwright-stealth` or `patchright` from the start; implement per-retailer delays (randomized 3-15s), fresh browser contexts per scrape, and a scrape health metric (success rate per retailer per day). Amazon has a ~2% baseline success rate for unprotected scrapers as of 2026.

2. **Playwright memory leaks crash the long-running process** — Never reuse browser contexts across scrape jobs; use `try/finally` to guarantee `context.close()` on every scrape; block unnecessary resources (images, CSS, fonts) to reduce memory pressure; limit concurrency to 2-3 pages maximum.

3. **APScheduler lifecycle mismanagement duplicates scrape jobs** — Use `AsyncIOScheduler` (not `BackgroundScheduler`), start/stop it inside FastAPI's `lifespan` context manager, run with `--workers 1` only. Multiple Uvicorn workers = multiple schedulers = N duplicate scrapes.

4. **SQLite "database is locked" under concurrent access** — Enable WAL mode and set `busy_timeout=5000` via SQLAlchemy event listener on every new connection. This must be done at database initialization, not retrofitted.

5. **CSS selectors break silently when retailers update layouts** — Implement a fallback selector hierarchy: JSON-LD structured data first, Open Graph meta tags second, multiple CSS selector candidates third, regex on page text as last resort. Use the `price-parser` library for price text parsing. Store raw extracted text alongside parsed values for debugging.

## Implications for Roadmap

Based on research, suggested phase structure (mirrors the dependency graph: Data → Scraping → API → Scheduling → Alerts/SSE → Frontend → Polish):

### Phase 1: Data Foundation
**Rationale:** Everything depends on the ability to read and write data. Alembic must be set up before any application code so schema evolution has a migration path from day one. WAL mode and busy_timeout must be configured on the first connection, not retrofitted.
**Delivers:** SQLAlchemy models for all 6 tables, Alembic migrations infrastructure, repository layer (CRUD for all tables), Pydantic schemas, WAL + busy_timeout pragmas on connection, integer-cents price storage
**Addresses:** Watch query data model, scrape result storage, alert records, scrape job tracking
**Avoids:** SQLite locking errors (Pitfall 4), no migration path (Pitfall 7), price float corruption (Pitfall 3 from architecture anti-patterns)

### Phase 2: Scraping Core
**Rationale:** The scraper is the product's entire value proposition. Validate it works — including anti-bot mitigations and memory management — before building any UI around it. A broken scraper discovered after the UI is built requires painful rework.
**Delivers:** BaseExtractor + AmazonExtractor (first retailer), shared Playwright browser manager, scraping service (load URL → extract → store result), `playwright-stealth` or `patchright` integration, per-retailer delay configuration, fresh context per scrape with try/finally cleanup, resource blocking (images/CSS/fonts), `price-parser` integration, CLI test script to validate without API
**Addresses:** Headless browser scraping, extract product name/price/URL, scrape failure handling, price delta calculation
**Avoids:** Anti-bot blocking (Pitfall 1), memory leaks (Pitfall 2), sync Playwright in async context (Pitfall 8), price parsing corruption (Pitfall 6), selector breakage (Pitfall 5)

### Phase 3: API Layer
**Rationale:** REST API wraps the validated scraping and data layer. With working scraping and data persistence confirmed, the API surface is clear and stable.
**Delivers:** FastAPI app skeleton with lifespan context, watch query CRUD endpoints, scrape results endpoints, alerts endpoints, on-demand scrape endpoint (POST /api/watch-queries/{id}/scrape returns 202), CORS configuration for React dev server
**Addresses:** Watch query CRUD, on-demand scrape trigger, alert log/history endpoints
**Avoids:** Scraping in request handlers (architecture anti-pattern 1)

### Phase 4: Scheduling
**Rationale:** Scheduling depends on working API and scraping layers. Job registration is tied to watch query lifecycle (create/update/delete/pause), which requires the API layer to exist.
**Delivers:** APScheduler AsyncIOScheduler in FastAPI lifespan, job registration on watch query create/update, job removal on delete/pause, startup job restoration from DB, per-retailer request queue with rate limiting and jitter, exponential backoff on HTTP errors
**Addresses:** Scheduled background scraping, configurable schedule per query (6h/12h/daily/weekly)
**Avoids:** APScheduler lifecycle bugs (Pitfall 3), rate limiting/IP bans (Pitfall 9), duplicate jobs from multiple workers

### Phase 5: Real-Time Alerts and SSE
**Rationale:** Alert evaluation and real-time push depend on a solid scraping pipeline. This phase wires the end-to-end value loop: scrape → detect threshold breach → push notification.
**Delivers:** SSE EventManager (asyncio queue pub/sub), alert evaluation in scraping service (price <= threshold creates Alert record), SSE push on alert creation, alert CRUD (mark read, list history, mark all read), scrape health metric (success rate per retailer), scrape status indicator per query
**Addresses:** Alert fires when price <= threshold, in-app notification badge/toast, alert log/history, mark alert as read/dismissed, scrape status indicators
**Avoids:** Frontend polling overload (Pitfall 10)

### Phase 6: Frontend
**Rationale:** Frontend consumes all backend APIs. Building it last means the API surface is stable, tested, and unlikely to change significantly. TanStack Query handles all server state; SSE EventSource handles real-time notifications.
**Delivers:** React + Vite + TypeScript scaffold, API client (typed fetch wrappers), Dashboard (all watch queries, cards with latest price/delta/status/last scrape), watch query CRUD forms (create/edit/pause/delete), price history line chart + table with threshold line and time range filter, SSE EventSource connection for alert toast/badge, alert log view, multi-retailer lowest-price highlighting, dark mode (Tailwind — implement now, not later)
**Addresses:** Dashboard overview, drill-down per query, price history chart, alert notifications, visual below-threshold indicators
**Uses:** React 19, Vite 8, TanStack Query 5.90+, Tailwind CSS 4.2+, Recharts 3.8+, FastAPI native SSE

### Phase 7: Polish and Additional Retailers
**Rationale:** Additional retailer extractors and UX polish are lower-risk and can be developed iteratively once the core loop is proven end-to-end.
**Delivers:** BestBuy extractor, Walmart extractor, Generic fallback extractor (JSON-LD / Open Graph), sparkline on dashboard cards, price drop percentage from peak, export price history to CSV, error handling UX (retry indicators, failure states), URL canonicalization (strip tracking params, store canonical product IDs), page type detection before parsing (in-stock vs. out-of-stock vs. marketplace)
**Addresses:** Multi-retailer support, differentiator features, selector resilience, URL stability
**Avoids:** URL expiration/tracking param corruption (Pitfall 12), retailer page variant handling (Pitfall 11)

### Phase Ordering Rationale

- Data before everything because every other layer depends on being able to read/write data, and migration tooling must exist before schema evolution begins
- Scraping before API because the scraper is the highest-risk component; discovering anti-bot issues or memory problems at Phase 2 is recoverable; discovering them at Phase 6 is not
- API before scheduling because job registration is coupled to watch query lifecycle; the CRUD endpoints must exist before scheduler integration can be implemented correctly
- Scheduling before alerts because alert evaluation happens inside the scraping flow, which the scheduler triggers
- Frontend last because it consumes all backend APIs; building it against stable, tested endpoints means the frontend reflects the actual API, not aspirational design

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Scraping Core):** Anti-bot bypass techniques are a moving target — specific `playwright-stealth` vs. `patchright` selection, Amazon-specific selector strategies, and stealth configuration may need targeted research at planning time to reflect the current 2026 state of anti-bot systems
- **Phase 2 (Scraping Core):** Retailer-specific CSS selector sets for Amazon/BestBuy/Walmart require empirical testing against live pages; selectors documented in research may already be stale

Phases with standard patterns (skip research-phase):
- **Phase 1 (Data Foundation):** SQLAlchemy 2.0 async + Alembic + SQLite WAL is a well-documented, stable pattern with official documentation and code examples already in STACK.md and ARCHITECTURE.md
- **Phase 3 (API Layer):** FastAPI CRUD endpoints and dependency injection are thoroughly documented; lifespan context manager pattern is explicitly provided in STACK.md
- **Phase 4 (Scheduling):** APScheduler 3.x + FastAPI lifespan integration pattern is explicitly documented with working code examples in both STACK.md and ARCHITECTURE.md
- **Phase 5 (Alerts/SSE):** FastAPI native SSE + asyncio queue EventManager pattern is fully specified in ARCHITECTURE.md
- **Phase 6 (Frontend):** TanStack Query + Vite + Tailwind 4 is conventional 2026 React stack with extensive documentation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified against official PyPI, release notes, and documentation. Version numbers confirmed. APScheduler 4.x instability explicitly confirmed by `fastapi-apscheduler4` package warnings. |
| Features | HIGH | Grounded in feature comparison of CamelCamelCamel, Keepa, PriceGhost, PriceBuddy, and multiple market overview sources. Feature dependencies charted explicitly. |
| Architecture | HIGH | Layer boundaries, data flow, schema design, and code patterns are all explicitly documented with working code examples. Confirmed against FastAPI best practices repo. |
| Pitfalls | HIGH | All 5 critical pitfalls confirmed by multiple independent authoritative sources. Playwright memory leak confirmed by GitHub issues. Amazon 2% success rate confirmed by multiple 2026-dated sources. SQLite WAL mode confirmed by Charles Leifer and SkyPilot. |

**Overall confidence:** HIGH

### Gaps to Address

- **Actual retailer CSS selectors:** The selector fallback strategy is well-defined, but the specific CSS selectors for Amazon/BestBuy/Walmart price elements must be validated against live pages at implementation time. Retailer frontends change frequently; selectors in any research document may be outdated within weeks.
- **`playwright-stealth` vs. `patchright` selection:** Both are recommended for anti-bot mitigation; the specific choice and configuration depends on current maintenance status and effectiveness as of implementation time. `patchright` is described as the newer fork. Validate before Phase 2.
- **Amazon Product Advertising API viability:** Research notes the PA API as a lower-detection alternative to direct scraping for Amazon. API access requires affiliate status. This is worth evaluating if direct Amazon scraping proves consistently blocked.
- **SQLite data volume limits:** For a long-running personal tool accumulating scrape results across many watch queries, the research notes that SQLite handles millions of rows fine but recommends partitioning `scrape_results` by date if the DB exceeds 1GB. No specific timeline projection was made; monitor in practice.

## Sources

### Primary (HIGH confidence)
- [FastAPI Release Notes](https://fastapi.tiangolo.com/release-notes/) — Native SSE support in 0.135+, version verification
- [FastAPI SSE Documentation](https://fastapi.tiangolo.com/tutorial/server-sent-events/) — Native SSE API
- [SQLAlchemy 2.0 Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — Async session patterns, expire_on_commit
- [Alembic Documentation](https://alembic.sqlalchemy.org/) — Migration tooling
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) — v3.11.2 stable, v4 not production-ready
- [fastapi-apscheduler4 PyPI](https://pypi.org/project/fastapi-apscheduler4/) — Explicit v4 production-readiness warning
- [Playwright Python Release Notes](https://playwright.dev/python/docs/release-notes) — v1.58
- [Vite 8.0 Announcement](https://vite.dev/blog/announcing-vite8) — Vite 8 with Rolldown/Oxc
- [Playwright Memory Issues #6319, #15400, #286](https://github.com/microsoft/playwright/issues/6319) — Memory leak confirmation
- [Multi-threaded SQLite - Charles Leifer](https://charlesleifer.com/blog/multi-threaded-sqlite-without-the-operationalerrors/) — WAL mode and locking
- [price-parser - PyPI](https://pypi.org/project/price-parser/) — Price text parsing library
- [FastAPI Best Practices - GitHub](https://github.com/zhanymkanov/fastapi-best-practices) — Project structure

### Secondary (MEDIUM confidence)
- [The 2026 Amazon Scraping Wars - Medium](https://medium.com/@pangolin.spg/the-2026-amazon-scraping-wars-a-technical-deep-dive-into-anti-bot-combat-b77503fe2418) — Amazon 2% success rate baseline, ML scoring
- [CamelCamelCamel vs Keepa](https://goaura.com/blog/camelcamelcamel-vs-keepa) — Feature comparison, market analysis
- [WebSocket vs SSE vs Polling 2025](https://potapov.me/en/make/websocket-sse-longpolling-realtime) — Protocol comparison
- [SQLite Concurrent Writes - SkyPilot](https://blog.skypilot.co/abusing-sqlite-to-handle-concurrency/) — WAL behavior
- [Zyte Scraping Architecture](https://www.zyte.com/learn/architecting-a-web-scraping-solution/) — Scraping system design
- [Oxylabs Walmart Scraping Guide 2026](https://oxylabs.io/blog/how-to-scrape-walmart-data) — Walmart anti-bot systems

### Tertiary (LOW confidence)
- [SSE with FastAPI - Medium](https://medium.com/@inandelibas/real-time-notifications-in-python-using-sse-with-fastapi-1c8c54746eb7) — SSE implementation patterns (pre-native-SSE article; validate against official docs)
- [Price Scraping Patterns - DEV](https://dev.to/hasdata_com/use-these-python-patterns-for-price-scraping-a2d) — Retailer extraction strategies (validate CSS selectors against live pages)

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*
