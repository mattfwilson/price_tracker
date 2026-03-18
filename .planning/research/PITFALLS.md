# Domain Pitfalls

**Domain:** Price scraping / price tracking web application
**Researched:** 2026-03-18

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or a fundamentally broken product.

---

### Pitfall 1: Retailer Anti-Bot Systems Will Block You on Day One

**What goes wrong:** You build the scraper against Amazon, Walmart, or Best Buy and it works in development with a handful of manual test runs. You deploy background scheduling and within hours you get CAPTCHAs, empty responses, IP blocks, or (Amazon's latest) AI-scored "human likelihood" rejection. As of 2026, a basic Python script against Amazon has roughly a 2% success rate without countermeasures. Amazon uses AWS WAF with real-time ML scoring. Walmart uses layered anti-bot analyzing IP, HTTP fingerprint, and JS environment. Cloudflare (used by many retailers) now deploys "AI Labyrinth" that feeds bots through infinite fake pages.

**Why it happens:** Developers build scraping logic against page structure and assume network access is the easy part. The opposite is true: parsing HTML is trivial; getting the HTML in the first place is the hard part.

**Consequences:** The entire core value proposition ("automated price tracking") silently fails. Scrape jobs return empty/stale data. Users see no price updates and lose trust in the tool.

**Prevention:**
- Accept that major retailers (Amazon, Walmart) are extremely hostile to scrapers. Design the scraper architecture with anti-detection as a first-class concern, not a bolt-on.
- Use `playwright-stealth` (or the newer `patchright` fork) from the start to mask automation fingerprints (`navigator.webdriver`, default user-agent, etc.).
- Implement per-retailer configuration: user-agent rotation, request delays (randomized 3-15 seconds between actions), viewport randomization.
- Create new browser contexts per scrape session and close them after. Never reuse a single long-lived context across scrapes.
- Add human-like interaction patterns: random mouse movements, scroll-then-click, variable typing speed.
- For Amazon specifically: consider scraping from Amazon product pages directly (not search results), which has lower detection rates. Alternatively, use the Amazon Product Advertising API if the volume is low enough.
- Build a "scrape health" dashboard metric from day one: success rate per retailer per day. When it drops below 80%, alert.

**Detection:** Scrape results returning null prices, HTML containing CAPTCHA elements, HTTP 403/429 responses, response bodies that are much smaller than expected.

**Phase relevance:** Must be addressed in Phase 1 (core scraping). If you skip this, nothing else matters.

**Confidence:** HIGH -- multiple authoritative sources confirm the severity. Amazon's 2% baseline success rate is widely reported.

---

### Pitfall 2: Playwright Memory Leaks Kill the Long-Running FastAPI Process

**What goes wrong:** Playwright browser contexts and pages accumulate memory over time. The FastAPI + APScheduler process runs continuously. After hours or days of scheduled scrapes, memory usage climbs to gigabytes and the process either OOM-crashes or becomes unresponsive. Reloading a page does not free the memory -- only closing the page and recreating it does. Internal HashMaps (Request/Response objects) in Playwright's connection layer are never cleared during a context's lifetime.

**Why it happens:** Developers reuse browser instances or contexts across scrape jobs for "efficiency." Each scrape accumulates DOM nodes, cached resources, event listeners, and network response buffers in memory. Playwright was designed for test suites (short-lived), not for 24/7 scraping daemons.

**Consequences:** The background service silently degrades and eventually crashes. Scheduled scrapes start failing. On a local machine without process monitoring, the user may not notice for days.

**Prevention:**
- Never reuse browser contexts across scrape jobs. Create a fresh context per scrape batch, do the work, close the context, close the browser. Every time.
- Use `browser.new_context()` and `context.close()` in a try/finally block (or async context manager) so contexts are always cleaned up, even on exceptions.
- Set a hard memory ceiling: monitor process RSS and restart the Playwright browser instance if it exceeds a threshold (e.g., 500MB).
- Limit concurrency: don't open 20 pages simultaneously. Process URLs sequentially or in small batches (2-3 concurrent pages max).
- Disable unnecessary resource loading: `context.route("**/*.{png,jpg,gif,svg,css,font,woff}", lambda route: route.abort())` to skip images/CSS/fonts that waste memory and bandwidth.

**Detection:** Monotonically increasing memory usage over successive scrape cycles. Process RSS growing beyond 300-500MB.

**Phase relevance:** Must be designed into the scraping service architecture in Phase 1. Retrofitting context lifecycle management is painful.

**Confidence:** HIGH -- confirmed via multiple Playwright GitHub issues (#6319, #15400, #286) and community reports.

---

### Pitfall 3: APScheduler + FastAPI Lifecycle Mismanagement

**What goes wrong:** APScheduler's scheduler is initialized incorrectly relative to FastAPI's lifecycle. Common failure modes: (a) scheduler starts before the event loop is ready, (b) scheduler blocks the event loop and FastAPI stops responding to HTTP requests, (c) using `BackgroundScheduler` (thread-based) instead of `AsyncIOScheduler` creates thread-safety issues with async code, (d) if running with multiple Uvicorn workers, each worker spawns its own scheduler instance, causing duplicate scrape jobs.

**Why it happens:** APScheduler and FastAPI have independent lifecycle models. FastAPI manages startup/shutdown via lifespan context managers. APScheduler needs to be explicitly started and stopped. Developers often start the scheduler at module import time or in a startup event without proper shutdown handling.

**Consequences:** Duplicate scrape jobs waste resources and may trigger anti-bot detection faster. Blocked event loops make the UI unresponsive. Improperly shut down schedulers leave orphaned browser processes.

**Prevention:**
- Use `AsyncIOScheduler` (not `BackgroundScheduler`) so jobs run on the same event loop as FastAPI.
- Initialize and start the scheduler inside FastAPI's `lifespan` async context manager. Shut it down in the teardown phase of the same lifespan.
- Run Uvicorn with `--workers 1` for this application. Multiple workers means multiple schedulers. For a single-user local tool, one worker is correct.
- Make all scheduled job functions `async def` so they cooperate with the event loop. Never run synchronous Playwright calls from an async scheduler job -- use `async_playwright`.
- Add a file-lock guard as defense-in-depth against accidental multi-instance scheduling.

**Detection:** Seeing the same scrape job execute multiple times at the same scheduled time (check logs). FastAPI endpoints becoming unresponsive during scrape cycles.

**Phase relevance:** Phase 1/2 (scheduling infrastructure). Must be correct before building the full scrape schedule UI.

**Confidence:** HIGH -- confirmed via APScheduler GitHub issues and FastAPI integration guides.

---

### Pitfall 4: SQLite "Database Is Locked" Under Concurrent Access

**What goes wrong:** The APScheduler job writes scrape results to SQLite at the same time the FastAPI endpoint reads data for the dashboard. SQLite uses database-level locking. With Python's default `pysqlite` driver, transactions are implicitly opened on the first write and held open longer than expected. Result: `sqlite3.OperationalError: database is locked` errors that crash scrape jobs or API responses.

**Why it happens:** SQLite is single-writer. Python's `pysqlite` has a "clunky transaction state-machine" that silently holds write locks longer than necessary. Developers assume SQLite handles concurrency like PostgreSQL because reads work fine in isolation.

**Consequences:** Scrape results are silently lost (write fails, no retry). Dashboard shows stale data or errors. In the worst case, data corruption if transactions are interrupted.

**Prevention:**
- Enable WAL (Write-Ahead Logging) mode immediately: `PRAGMA journal_mode=WAL;` This allows concurrent reads while a write is in progress. This is the single most impactful SQLite configuration for this use case.
- Set a generous busy timeout: `PRAGMA busy_timeout=5000;` (5 seconds). This makes SQLite retry internally instead of immediately raising an error.
- Keep write transactions as short as possible. Batch-insert scrape results in a single transaction, don't hold the transaction open while parsing HTML.
- Use a single shared connection for writes (or a connection pool with max 1 writer). The async context makes this natural: all DB writes go through one async function that serializes access.
- If using SQLAlchemy or an async ORM like `aiosqlite`, configure it to pass through the PRAGMA settings on each new connection via an event listener.

**Detection:** Any `OperationalError: database is locked` in logs. Scrape results missing from the database despite the scraper reporting success.

**Phase relevance:** Phase 1 (data layer setup). WAL mode and busy_timeout must be set when the database is first created.

**Confidence:** HIGH -- well-documented SQLite limitation, confirmed by multiple sources including Charles Leifer's SQLite guides.

---

### Pitfall 5: CSS Selectors Break Silently When Retailers Update Their Layouts

**What goes wrong:** You write a CSS selector like `.a-price .a-offscreen` to extract the price from Amazon. Amazon A/B tests a new layout, changes a class name, or restructures the DOM. Your selector returns `None` instead of a price. The scraper logs "no price found," stores nothing, and moves on. No crash, no error -- just silent data loss. This happens routinely; major retailers update frontend code weekly.

**Why it happens:** CSS selectors encode a structural assumption about the page. Retailer frontends are built for users, not scrapers. Class names like `.s-price-col` are generated by build tools and change without notice.

**Consequences:** Price tracking silently stops working for affected retailers. The user sees stale "last scraped" timestamps but may not realize the scraper is failing until they miss a price drop they were watching.

**Prevention:**
- Implement a per-retailer scraper module pattern. Each retailer gets its own file with its own selectors and parsing logic. When a selector breaks, the fix is isolated.
- Use multiple fallback selectors per price element. Try the primary selector, then a secondary, then a regex-based text extraction as last resort.
- Prefer semantic selectors over structural ones: `[data-testid="price"]`, `[itemprop="price"]`, `meta[property="og:price:amount"]` are more stable than class-based selectors.
- Use the `price-parser` library (by Scrapinghub/Zyte) to extract price amounts from raw text strings instead of writing custom regex. It handles 900+ real-world price format variations.
- Build a "selector health check" that runs after each scrape: if a retailer returns 0 prices out of N expected results, flag it as broken in the UI and log a warning.
- Store the raw HTML snapshot (or at least a relevant snippet) when a selector fails, so you can debug what changed without re-scraping.

**Detection:** Sudden drop in successful price extractions for a specific retailer. "Last successful scrape" timestamp going stale.

**Phase relevance:** Phase 1 (scraper architecture). The per-retailer module pattern and fallback strategy must be designed upfront.

**Confidence:** HIGH -- universally acknowledged as the #1 ongoing maintenance cost for any web scraper.

---

## Moderate Pitfalls

---

### Pitfall 6: Price Parsing Edge Cases Corrupt Your Data

**What goes wrong:** Prices appear in wildly different formats: `$1,299.00`, `1.299,00 EUR`, `$12.99 - $24.99` (range), `From $599`, `was $999 now $749` (strikethrough), empty string (sold out), `Currently unavailable`, or just a bare number with no currency symbol. Naive regex like `r'\$[\d,.]+'` mishandles most of these.

**Why it happens:** Developers test with a handful of clean prices and miss the long tail of formatting variations, especially multi-price elements (original + sale), range prices, and stock-out states.

**Prevention:**
- Use the `price-parser` library (`pip install price-parser`) as the primary parsing layer. It returns `Decimal` amounts and handles thousands/decimal separator ambiguity.
- Treat "out of stock" / "currently unavailable" / "sold out" as a distinct scrape result status, not as a parsing failure. Store it as `status: OUT_OF_STOCK` with `price: null`.
- When a page shows multiple prices (original + sale), extract both but store the lowest visible price as the "current price" and the higher one as "original price."
- Store prices as integers in cents (e.g., `12999` for `$129.99`) to avoid floating-point precision issues. Parse to `Decimal` first, multiply by 100, store as integer.
- Always store the raw extracted text alongside the parsed value so you can audit parsing correctness.

**Detection:** Prices that are 100x too high or too low (missed decimal separator). Price history charts showing impossible spikes.

**Phase relevance:** Phase 1 (scraping/parsing). The data model must accommodate null prices and status flags from the start.

**Confidence:** HIGH -- well-documented, price-parser library specifically built to address this.

---

### Pitfall 7: No Schema Migration Strategy Means Painful Database Changes

**What goes wrong:** You create the SQLite tables with raw `CREATE TABLE` statements. Two weeks later, you need to add an `original_price` column, or change `price` from REAL to INTEGER (cents). You have no migration tool, so you either write ad-hoc `ALTER TABLE` scripts that may lose data, or you delete the database and lose all historical price data.

**Why it happens:** For a "simple SQLite app," developers skip migration tooling as overkill. But the schema will change -- price tracking apps inevitably need new columns (currency, stock status, retailer metadata, alert configuration).

**Prevention:**
- Use Alembic (SQLAlchemy's migration tool) from day one, even for SQLite. The setup cost is 15 minutes. The cost of not having it is hours of manual migration scripting or data loss.
- Define models with SQLAlchemy ORM (or SQLModel for FastAPI-native feel) rather than raw SQL. This gives you a single source of truth for the schema.
- Design the initial schema with known future columns in mind: include `currency`, `status` (enum: OK/OUT_OF_STOCK/ERROR), `original_price`, `raw_text` from the start even if the UI doesn't use them yet.

**Detection:** Needing to change the schema and realizing there's no migration path.

**Phase relevance:** Phase 1 (data layer). Set up Alembic and initial migration before writing any application code.

**Confidence:** MEDIUM -- based on common patterns in small Python projects. Not specific to scraping but highly relevant given the domain's evolving data needs.

---

### Pitfall 8: Playwright Async/Sync Confusion in FastAPI Context

**What goes wrong:** Playwright offers both sync (`sync_playwright`) and async (`async_playwright`) APIs. Developers use the sync API because it's simpler, then discover it blocks the FastAPI event loop. The entire API becomes unresponsive during scrapes. Alternatively, they mix sync and async Playwright calls, creating deadlocks or "event loop already running" errors.

**Why it happens:** Playwright's sync API is more prominently documented and easier to get started with. The async API requires understanding `async with`, `await`, and proper context management.

**Prevention:**
- Use `async_playwright` exclusively. Never import from `playwright.sync_api` anywhere in the codebase.
- All scraper functions must be `async def`. The APScheduler job handler, the on-demand scrape endpoint, and the retry logic must all be async.
- If you must call a blocking library from async code, use `asyncio.to_thread()` -- but this should not be needed for Playwright's async API.
- Add a linting rule or code review check: any import of `playwright.sync_api` is a bug.

**Detection:** FastAPI endpoints timing out or becoming unresponsive when a scrape is running. "Event loop is already running" errors.

**Phase relevance:** Phase 1. The wrong choice here requires rewriting every scraper function.

**Confidence:** HIGH -- this is a well-known footgun in the Playwright + async Python ecosystem.

---

### Pitfall 9: No Rate Limiting or Backoff Leads to IP Bans

**What goes wrong:** A user creates 50 watch queries across 3 retailers. The scheduler fires all of them simultaneously. The scraper opens 50 browser pages and hits Walmart 20 times in 10 seconds. Walmart blocks the IP. Now all Walmart scrapes fail until the ban expires (hours or days).

**Why it happens:** Developers build the scheduler to fire all jobs at the configured interval without considering aggregate request volume across all watch queries targeting the same retailer.

**Consequences:** Temporary or permanent IP bans from retailers. All watch queries for that retailer fail. On a home IP without rotation, recovery may require waiting 24+ hours.

**Prevention:**
- Implement a per-retailer request queue with configurable rate limits (e.g., max 1 request per 10 seconds per retailer).
- Never scrape the same retailer in parallel. Serialize requests to each retailer with randomized delays (5-15 seconds between requests).
- Stagger scheduled scrape jobs: don't run all 50 watch queries at exactly 06:00. Add jitter: `scheduled_time + random(0, 300)` seconds.
- Implement exponential backoff on HTTP errors: if a retailer returns 429 or 403, wait 1min, then 5min, then 30min before retrying.
- Store the last request timestamp per retailer and enforce minimum intervals at the scraper layer, independent of scheduling.

**Detection:** Sudden spike in failed scrapes for a single retailer. HTTP 429 or CAPTCHA responses.

**Phase relevance:** Phase 1-2 (scraping infrastructure and scheduling).

**Confidence:** HIGH -- standard scraping operational knowledge.

---

## Minor Pitfalls

---

### Pitfall 10: Frontend Polling Overload on Dashboard

**What goes wrong:** The React dashboard polls the FastAPI backend every 2 seconds for "latest prices." With many watch queries, this creates unnecessary load and SQLite read contention. On slower machines, the UI feels sluggish.

**Prevention:**
- Use a longer poll interval (30-60 seconds) for the dashboard. Prices don't change between scrapes anyway.
- Better: use Server-Sent Events (SSE) from FastAPI to push updates only when a scrape completes. This eliminates polling entirely.
- Cache the dashboard summary response in memory (e.g., with a simple dict + timestamp) and invalidate only when new scrape results arrive.

**Detection:** High CPU usage from the FastAPI process even when no scrapes are running.

**Phase relevance:** Phase 3 (frontend/dashboard optimization).

---

### Pitfall 11: Not Handling Retailer-Specific Page Variants

**What goes wrong:** Amazon shows different page layouts for: product pages, search results, "Currently unavailable" pages, "Subscribe & Save" pricing, marketplace vs. Amazon-sold items, and regional variants. A single selector strategy per retailer is insufficient.

**Prevention:**
- Build retailer scrapers to detect the page type first (product page vs. search vs. out-of-stock), then apply the appropriate parsing strategy.
- Implement a page classification step before price extraction: check for known indicators ("Currently unavailable", "Add to Wish List" without price, etc.).
- Test each retailer scraper against at least 5 different product types (in-stock, out-of-stock, marketplace, sale price, subscription price).

**Detection:** Inconsistent parse results across different products on the same retailer.

**Phase relevance:** Phase 2 (retailer scraper hardening).

---

### Pitfall 12: Storing Absolute URLs That Expire or Change

**What goes wrong:** You store the full URL scraped from a search result. The URL contains session tokens, tracking parameters, or temporary redirect paths. A week later, the stored URL returns a 404 or redirects to the homepage.

**Prevention:**
- Canonicalize URLs before storage: strip tracking parameters (`utm_*`, `ref`, `tag`, session IDs).
- For Amazon, extract and store the ASIN; reconstruct the URL as `https://amazon.com/dp/{ASIN}`. For Walmart, store the product ID. Canonical identifiers are more stable than full URLs.
- Validate stored URLs periodically by checking for redirects/404s during scrape cycles.

**Detection:** Stored URLs returning 404 or redirecting to non-product pages.

**Phase relevance:** Phase 1 (data model design).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Core scraping engine | Anti-bot detection blocks all scrapes (Pitfall 1) | Stealth mode, delays, per-retailer config from day one |
| Core scraping engine | Memory leaks crash long-running process (Pitfall 2) | Fresh browser context per job, resource blocking, context cleanup in finally blocks |
| Data layer setup | SQLite locked errors (Pitfall 4) | WAL mode + busy_timeout on first connection |
| Data layer setup | No migration path (Pitfall 7) | Alembic + SQLAlchemy from day one |
| Scheduling | APScheduler lifecycle bugs (Pitfall 3) | AsyncIOScheduler in FastAPI lifespan, single worker |
| Scheduling | Rate limiting / IP bans (Pitfall 9) | Per-retailer queue with enforced delays and jitter |
| Price parsing | Silent data corruption (Pitfall 6) | price-parser library, store raw text, integer cents |
| Selector maintenance | Silent scraper breakage (Pitfall 5) | Fallback selectors, health checks, per-retailer modules |
| Frontend dashboard | Polling overhead (Pitfall 10) | SSE or long poll intervals, response caching |
| Retailer coverage | Page variant handling (Pitfall 11) | Page type detection before parsing, multi-variant test cases |

## Sources

- [Avoid Bot Detection With Playwright Stealth - Scrapeless](https://www.scrapeless.com/en/blog/avoid-bot-detection-with-playwright-stealth)
- [How to Avoid Bot Detection with Playwright - ZenRows](https://www.zenrows.com/blog/avoid-playwright-bot-detection)
- [Playwright Crawling Complete Guide 2026 - HashScraper](https://blog.hashscraper.com/posts/playwright-crawling-complete-guide-2026-from-installation-to-anti-bot-bypass-1?locale=en)
- [The 2026 Amazon Scraping Wars - Medium](https://medium.com/@pangolin.spg/the-2026-amazon-scraping-wars-a-technical-deep-dive-into-anti-bot-combat-b77503fe2418)
- [Does Amazon Allow Web Scraping? - DataPrixa](https://dataprixa.com/does-amazon-allow-web-scraping/)
- [How to Scrape Walmart in 2026 - Oxylabs](https://oxylabs.io/blog/how-to-scrape-walmart-data)
- [Playwright Memory Issue #6319 - GitHub](https://github.com/microsoft/playwright/issues/6319)
- [Playwright Memory Issue #15400 - GitHub](https://github.com/microsoft/playwright/issues/15400)
- [Playwright Python Memory Leak #286 - GitHub](https://github.com/microsoft/playwright-python/issues/286)
- [Memory Management Best Practices - WebScraping.AI](https://webscraping.ai/faq/playwright/what-are-the-memory-management-best-practices-when-running-long-playwright-sessions)
- [Schedule Tasks with FastAPI - Sentry](https://sentry.io/answers/schedule-tasks-with-fastapi/)
- [APScheduler FastAPI Integration - ByteGoblin](https://bytegoblin.io/blog/implementing-background-job-scheduling-in-fastapi-with-apscheduler.mdx)
- [SQLAlchemyJobStore Issue #499 - APScheduler GitHub](https://github.com/agronholm/apscheduler/issues/499)
- [Abusing SQLite to Handle Concurrency - SkyPilot](https://blog.skypilot.co/abusing-sqlite-to-handle-concurrency/)
- [Multi-threaded SQLite without OperationalErrors - Charles Leifer](https://charlesleifer.com/blog/multi-threaded-sqlite-without-the-operationalerrors/)
- [Concurrent Writing with SQLite3 in Python - PythonTutorials](https://www.pythontutorials.net/blog/concurrent-writing-with-sqlite3/)
- [price-parser - PyPI](https://pypi.org/project/price-parser/)
- [Price-Parser Python Guide - Piloterr](https://www.piloterr.com/blog/price-parser-python-guide-web-scraping)
- [Why XPath CSS Selectors Break Scrapers - ExtractData](https://extractdata.substack.com/p/why-xpath-css-selectors-break-scrapers)
- [Why Your Web Scraper Keeps Breaking - BinaryBits](https://binarybits.co/blog/why-web-scraper-keeps-breaking)
- [Price Scraping Guide 2026 - ProxyScrape](https://proxyscrape.com/blog/scraping-prices-from-websites)
