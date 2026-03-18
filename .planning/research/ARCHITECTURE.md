# Architecture Patterns

**Domain:** Price scraping / price tracking web application
**Researched:** 2026-03-18

## Recommended Architecture

Single-process monolith with four clearly separated internal layers. FastAPI serves both the REST API and the React SPA (static build). APScheduler runs in-process, sharing the same event loop. SQLite is the sole data store, accessed through SQLAlchemy async (via aiosqlite). Playwright runs headless Chromium for scraping.

```
+------------------------------------------------------------------+
|  Browser (React SPA)                                             |
|  - Dashboard, watch query CRUD, price history charts, alerts     |
|  - Connects via REST + SSE for real-time alert notifications     |
+------------------------------------------------------------------+
        |  HTTP REST  |  SSE (server-push)
        v             v
+------------------------------------------------------------------+
|  FastAPI Application Process                                     |
|                                                                  |
|  +------------------+  +------------------+  +----------------+  |
|  |  API Layer       |  |  Scheduler Layer |  |  SSE Manager   |  |
|  |  (routers/)      |  |  (APScheduler)   |  |  (event bus)   |  |
|  +--------+---------+  +--------+---------+  +-------+--------+  |
|           |                      |                    ^           |
|           v                      v                    |           |
|  +------------------+  +------------------+           |           |
|  |  Service Layer   |  |  Scraping Service|----notify-+           |
|  |  (services/)     |  |  (scrapers/)     |                      |
|  +--------+---------+  +--------+---------+                      |
|           |                      |                                |
|           v                      v                                |
|  +-----------------------------------------------+               |
|  |  Data Layer (models/, repositories/, schemas/) |               |
|  |  SQLAlchemy async ORM  +  aiosqlite           |               |
|  +-----------------------------------------------+               |
|           |                                                      |
|           v                                                      |
|  +-------------------+                                           |
|  |  SQLite (WAL mode)|                                           |
|  |  price_scraper.db |                                           |
|  +-------------------+                                           |
+------------------------------------------------------------------+
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **React Frontend** | UI rendering, user interaction, data visualization (charts), alert display | API Layer (REST), SSE Manager (EventSource) |
| **API Layer** (`routers/`) | HTTP request handling, input validation, response serialization | Service Layer, SSE Manager |
| **Service Layer** (`services/`) | Business logic: CRUD for watch queries, alert evaluation, price delta calculation | Data Layer, Scraping Service, SSE Manager |
| **Scraping Service** (`scrapers/`) | Playwright browser automation, retailer-specific extraction, retry logic | Data Layer (writes results), SSE Manager (emits events) |
| **Scheduler Layer** | APScheduler lifecycle, job registration/removal, cron/interval triggers | Scraping Service (invokes scrape jobs) |
| **SSE Manager** | In-memory event bus, manages active SSE connections, pushes notifications | Frontend (SSE stream) |
| **Data Layer** (`models/`, `repositories/`) | SQLAlchemy models, database queries, session management | SQLite database |

### Key Boundary Rules

1. **Routers never import scrapers directly.** Routers call services; services orchestrate scrapers.
2. **Scrapers never import routers.** Scrapers write to DB via repositories, then emit events to the SSE manager.
3. **The scheduler only calls service-layer functions.** It does not contain business logic itself.
4. **The frontend never talks to the scheduler directly.** On-demand scrapes go through a REST endpoint that invokes the service layer.

## Data Flow

### Primary Flow: Scheduled Scrape

```
1. APScheduler fires interval/cron trigger
2. Scheduler calls scraping_service.run_scrape(watch_query_id)
3. scraping_service loads WatchQuery + its retailer URLs from DB
4. For each retailer URL:
   a. Scraping service selects the appropriate retailer extractor
   b. Playwright launches page, waits for content, extracts price data
   c. Result (product_name, price, url, timestamp) written to ScrapeResult table
   d. Price delta calculated vs. previous ScrapeResult for same listing
5. Alert evaluation: if price <= threshold, create Alert record
6. If alert created: push event to SSE manager
7. SSE manager fans out to all connected EventSource clients
8. React frontend shows toast notification + updates badge count
```

### Secondary Flow: On-Demand Scrape

```
1. User clicks "Scrape Now" in React UI
2. POST /api/watch-queries/{id}/scrape
3. Router calls scraping_service.run_scrape(watch_query_id)
4. Same steps 3-8 as above
5. Response returns scrape status (started/completed) to frontend
```

### Secondary Flow: Watch Query CRUD

```
1. User creates/edits watch query in React UI
2. POST/PUT /api/watch-queries/
3. Router validates via Pydantic schema, calls watch_query_service
4. Service persists to DB
5. Service registers/updates APScheduler job with new schedule
6. Response returns created/updated watch query
```

## Database Schema Shape

Six tables covering the core domain. SQLite with WAL mode enabled for concurrent read/write.

```
+-------------------+       +----------------------+
| watch_queries     |       | retailer_urls        |
+-------------------+       +----------------------+
| id (PK)           |<------| id (PK)              |
| name              |       | watch_query_id (FK)  |
| search_term       |       | url                  |
| price_threshold   |       | retailer_name        |
| schedule_type     |       | created_at           |
| schedule_interval |       +----------------------+
| is_active         |                |
| created_at        |                |
| updated_at        |                v
+-------------------+       +----------------------+
                            | scrape_results       |
                            +----------------------+
                            | id (PK)              |
                            | retailer_url_id (FK) |
                            | product_name         |
                            | price (DECIMAL)      |
                            | listing_url          |
                            | price_delta          |
                            | status (enum)        |
                            | error_message        |
                            | scraped_at           |
                            +----------------------+
                                     |
                                     v
+-------------------+       +----------------------+
| alerts            |       | scrape_jobs          |
+-------------------+       +----------------------+
| id (PK)           |       | id (PK)              |
| watch_query_id(FK)|       | watch_query_id (FK)  |
| scrape_result_id  |       | apscheduler_job_id   |
| threshold_at_time |       | schedule_type        |
| triggered_price   |       | schedule_value       |
| is_read           |       | last_run_at          |
| created_at        |       | next_run_at          |
+-------------------+       | status               |
                            +----------------------+

+-------------------+
| app_settings      |
+-------------------+
| key (PK)          |
| value             |
+-------------------+
```

**Schema notes:**
- `price` stored as integer cents (e.g., 1999 = $19.99) to avoid floating-point issues. Never use FLOAT for money.
- `price_delta` is computed on write: current price minus previous price for the same retailer_url_id.
- `scrape_jobs` mirrors APScheduler state for UI display. APScheduler's own job store is separate (its default memory store is fine for single-process).
- `app_settings` is a simple key-value table for global config (default schedule, etc.).
- `status` enum on scrape_results: `success`, `failed`, `pending`.

## Project Directory Structure

```
price_scraper/
+-- backend/
|   +-- app/
|   |   +-- __init__.py
|   |   +-- main.py              # FastAPI app, lifespan, CORS, static mount
|   |   +-- config.py            # Settings via pydantic-settings
|   |   +-- database.py          # Engine, session factory, WAL pragma
|   |   +-- routers/
|   |   |   +-- watch_queries.py
|   |   |   +-- scrape_results.py
|   |   |   +-- alerts.py
|   |   |   +-- events.py        # SSE endpoint
|   |   +-- services/
|   |   |   +-- watch_query_service.py
|   |   |   +-- scraping_service.py
|   |   |   +-- alert_service.py
|   |   +-- scrapers/
|   |   |   +-- base.py           # Abstract base extractor
|   |   |   +-- amazon.py
|   |   |   +-- bestbuy.py
|   |   |   +-- walmart.py
|   |   |   +-- generic.py        # Fallback: JSON-LD / Open Graph
|   |   +-- models/
|   |   |   +-- watch_query.py
|   |   |   +-- retailer_url.py
|   |   |   +-- scrape_result.py
|   |   |   +-- alert.py
|   |   +-- schemas/              # Pydantic request/response models
|   |   |   +-- watch_query.py
|   |   |   +-- scrape_result.py
|   |   |   +-- alert.py
|   |   +-- repositories/        # DB query functions (thin ORM layer)
|   |   |   +-- watch_query_repo.py
|   |   |   +-- scrape_result_repo.py
|   |   |   +-- alert_repo.py
|   |   +-- scheduler/
|   |   |   +-- setup.py          # APScheduler config, lifespan integration
|   |   |   +-- jobs.py           # Job functions (thin wrappers around services)
|   |   +-- events/
|   |   |   +-- manager.py        # SSE connection manager + event bus
|   +-- alembic/                  # DB migrations
|   +-- tests/
|   +-- requirements.txt
+-- frontend/
|   +-- src/
|   |   +-- components/
|   |   +-- pages/
|   |   +-- hooks/
|   |   +-- api/                  # API client (fetch wrappers)
|   |   +-- types/
|   +-- package.json
+-- README.md
```

## Patterns to Follow

### Pattern 1: Retailer Extractor Strategy

Each retailer gets its own extractor class inheriting from a base. This isolates selector logic per site and makes adding new retailers straightforward.

**What:** Strategy pattern for retailer-specific scraping logic.
**When:** Every scrape operation.
**Example:**
```python
# scrapers/base.py
from abc import ABC, abstractmethod
from playwright.async_api import Page
from dataclasses import dataclass

@dataclass
class ScrapeData:
    product_name: str
    price_cents: int          # Always store as cents
    listing_url: str

class BaseExtractor(ABC):
    """One per retailer. Encapsulates all selector/parsing logic."""

    @abstractmethod
    async def extract(self, page: Page, url: str) -> ScrapeData:
        """Navigate to URL and extract price data."""
        ...

    @abstractmethod
    def matches(self, url: str) -> bool:
        """Return True if this extractor handles the given URL."""
        ...

# scrapers/amazon.py
class AmazonExtractor(BaseExtractor):
    def matches(self, url: str) -> bool:
        return "amazon.com" in url or "amazon.ca" in url

    async def extract(self, page: Page, url: str) -> ScrapeData:
        await page.goto(url, wait_until="domcontentloaded")
        # Try JSON-LD first (most reliable)
        json_ld = await self._try_json_ld(page)
        if json_ld:
            return json_ld
        # Fall back to selectors
        price_el = await page.query_selector("#priceblock_ourprice, .a-price .a-offscreen")
        ...
```

### Pattern 2: APScheduler Lifespan Integration

**What:** Start/stop APScheduler tied to FastAPI's lifespan context manager.
**When:** Application startup/shutdown.
**Example:**
```python
# main.py
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init Playwright browser, start scheduler
    app.state.browser = await playwright_manager.launch()
    scheduler.start()
    # Re-register jobs from DB for watch queries marked active
    await restore_scheduled_jobs(scheduler)
    yield
    # Shutdown: stop scheduler, close browser
    scheduler.shutdown(wait=False)
    await app.state.browser.close()

app = FastAPI(lifespan=lifespan)
```

### Pattern 3: SSE for Real-Time Alerts (Not WebSocket)

**What:** Server-Sent Events for pushing alert notifications to the frontend.
**Why SSE over WebSocket:** Communication is unidirectional (server to client only). SSE auto-reconnects natively in browsers. Simpler to implement. No bidirectional channel needed -- user actions go through REST.
**When:** Alert fires, scrape status updates.
**Example:**
```python
# events/manager.py
import asyncio
from typing import AsyncGenerator

class EventManager:
    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    async def subscribe(self) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        finally:
            self._subscribers.remove(queue)

    async def publish(self, event_data: str):
        for queue in self._subscribers:
            await queue.put(event_data)

event_manager = EventManager()

# routers/events.py
from sse_starlette.sse import EventSourceResponse

@router.get("/events")
async def event_stream():
    return EventSourceResponse(event_manager.subscribe())
```

### Pattern 4: Shared Playwright Browser Instance

**What:** Single Playwright browser instance shared across all scrape jobs, with a new context/page per scrape.
**Why:** Launching a browser is expensive (~1-2s). Reusing one browser and creating lightweight contexts per scrape is much faster.
**When:** Application lifetime.
**Example:**
```python
# Each scrape gets a fresh context (isolated cookies, no state leaking)
async def run_single_scrape(browser, url, extractor):
    context = await browser.new_context()
    page = await context.new_page()
    try:
        result = await extractor.extract(page, url)
        return result
    finally:
        await context.close()
```

### Pattern 5: SQLite WAL Mode on Startup

**What:** Enable WAL mode and set pragmas at connection time for better concurrency.
**When:** Database initialization.
**Example:**
```python
# database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./price_scraper.db"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Scraping in the Request Handler

**What:** Running Playwright scraping synchronously inside an API route handler.
**Why bad:** Scrapes take 5-30 seconds. This blocks the response and times out the client. Even async, it holds the connection open pointlessly.
**Instead:** API endpoint triggers the scrape via the service layer, which can run it as a background task or scheduled job. Return 202 Accepted immediately. Push results via SSE when done.

### Anti-Pattern 2: One Browser Per Scrape

**What:** Calling `playwright.chromium.launch()` for every single scrape.
**Why bad:** Browser launch takes 1-2 seconds and ~100MB RAM each time. With 20 watch queries, you are launching 20 browsers.
**Instead:** Single browser instance at app startup, new `browser.new_context()` per scrape (milliseconds, isolated).

### Anti-Pattern 3: Storing Prices as Floats

**What:** Using `REAL` / `FLOAT` column type for prices.
**Why bad:** `19.99 + 0.01 = 20.000000000000004`. Comparison operators break. Accumulated rounding errors in historical data.
**Instead:** Store as integer cents. Display formatting is a frontend concern.

### Anti-Pattern 4: Hardcoded Selectors Without Fallback

**What:** Single CSS selector per retailer with no fallback strategy.
**Why bad:** Retailers change their DOM frequently. One class name change breaks all scraping for that site.
**Instead:** Selector hierarchy: JSON-LD structured data first, then Open Graph meta tags, then multiple CSS selector candidates, then regex on page text as last resort.

### Anti-Pattern 5: APScheduler in Multiple Workers

**What:** Running FastAPI with multiple Uvicorn workers when APScheduler is in-process.
**Why bad:** Each worker spawns its own scheduler. N workers = N duplicate scrapes for every job.
**Instead:** Single Uvicorn worker (`--workers 1`). For a personal local app, this is perfectly adequate. If you ever need multiple workers, extract the scheduler to a separate process.

## Notification Delivery: SSE

**Recommendation: Server-Sent Events (SSE)** over WebSocket or polling.

| Criterion | SSE | WebSocket | Polling |
|-----------|-----|-----------|---------|
| Direction | Server -> Client | Bidirectional | Client -> Server |
| Complexity | Low | Medium | Low |
| Auto-reconnect | Built-in | Manual | N/A |
| HTTP/2 compatible | Yes | Separate protocol | Yes |
| Use case fit | Alerts are server-push only | Overkill for this use case | Wasteful, delayed |

SSE is the right choice because:
- All real-time data flows one direction (server to client): alert fired, scrape completed, scrape failed.
- The browser's `EventSource` API handles reconnection automatically.
- No need for a WebSocket library on the frontend.
- The `sse-starlette` package integrates cleanly with FastAPI.
- For a single-user local app, connection management is trivial (one connection).

## Suggested Build Order

Build order is driven by dependency chains. Each phase should produce something testable.

```
Phase 1: Data Foundation
  - SQLAlchemy models + database.py + WAL pragma setup
  - Alembic migrations infrastructure
  - Repository layer (CRUD for all tables)
  - Pydantic schemas
  WHY FIRST: Everything else depends on being able to read/write data.

Phase 2: Scraping Core
  - BaseExtractor + one retailer extractor (Amazon or generic)
  - Playwright browser manager (shared instance pattern)
  - Scraping service (orchestrates: load URL -> extract -> store result)
  - Test with a CLI script (no API needed yet)
  WHY SECOND: The scraper is the product's core value. Validate it works
  before building UI around it.

Phase 3: API Layer
  - FastAPI app skeleton + lifespan
  - Watch query CRUD routes
  - Scrape results routes
  - Alerts routes
  - On-demand scrape endpoint
  WHY THIRD: REST API wraps the working scraping + data layer.

Phase 4: Scheduling
  - APScheduler setup + lifespan integration
  - Job registration when watch query is created/updated
  - Job removal when watch query is deleted/paused
  - Restore jobs from DB on startup
  WHY FOURTH: Scheduling depends on working API + scraping layers.

Phase 5: Real-Time + Alerts
  - SSE event manager
  - Alert evaluation in scraping service (price <= threshold)
  - SSE push on alert creation
  - Alert CRUD routes (mark read, list history)
  WHY FIFTH: Alerts depend on scraping pipeline being solid.

Phase 6: Frontend
  - React app scaffold + API client
  - Dashboard (list watch queries + latest results)
  - Watch query CRUD forms
  - Price history table + chart
  - SSE connection + alert toast/badge
  WHY LAST: Frontend consumes all backend APIs. Building it last means
  APIs are stable and tested.

Phase 7: Polish + Additional Retailers
  - Add BestBuy, Walmart extractors
  - Error handling UX (retry indicators, failure states)
  - README with setup + "add a retailer" guide
```

**Dependency graph:**
```
Data Layer --> Scraping Core --> API Layer --> Scheduling --> Alerts/SSE --> Frontend
                                                                             |
                                                            Additional Retailers (parallel)
```

## Scalability Considerations

This is a single-user local application. Scalability is not a primary concern, but the architecture should not paint itself into a corner.

| Concern | Single user (v1) | If needs grow |
|---------|-------------------|---------------|
| Concurrent scrapes | Sequential or 2-3 parallel contexts | Playwright browser pool with semaphore |
| Database size | SQLite handles millions of rows fine | Partition old scrape_results by date if > 1GB |
| Scheduler | In-process APScheduler | Extract to separate process + Redis job store |
| Frontend updates | Single SSE connection | Still fine with SSE for < 100 connections |
| Multiple workers | Single Uvicorn worker | Separate scheduler process, then scale API workers |

## Sources

- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) - Official docs on background processing
- [APScheduler User Guide (3.x)](https://apscheduler.readthedocs.io/en/3.x/userguide.html) - Scheduler configuration and job stores
- [SQLAlchemy 2.0 SQLite Dialect](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html) - SQLite-specific configuration including WAL
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) - Official WebSocket docs (used for comparison)
- [FastAPI SQL Databases Tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/) - Official SQLAlchemy integration guide
- [SSE with FastAPI - Medium](https://medium.com/@inandelibas/real-time-notifications-in-python-using-sse-with-fastapi-1c8c54746eb7) - SSE implementation patterns (MEDIUM confidence)
- [APScheduler + FastAPI Integration - Medium](https://rajansahu713.medium.com/implementing-background-job-scheduling-in-fastapi-with-apscheduler-6f5fdabf3186) - Lifespan integration pattern (MEDIUM confidence)
- [SQLite Concurrent Writes](https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/) - WAL mode and locking behavior
- [WebSocket vs SSE vs Polling 2025](https://potapov.me/en/make/websocket-sse-longpolling-realtime) - Real-time protocol comparison (MEDIUM confidence)
- [FastAPI Best Practices - GitHub](https://github.com/zhanymkanov/fastapi-best-practices) - Project structure conventions
- [Zyte Scraping Architecture](https://www.zyte.com/learn/architecting-a-web-scraping-solution/) - Scraping system design patterns
- [Price Scraping Patterns - DEV](https://dev.to/hasdata_com/use-these-python-patterns-for-price-scraping-a2d) - Retailer extraction strategies (MEDIUM confidence)
