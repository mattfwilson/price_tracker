# Technology Stack

**Project:** Price Scraper
**Researched:** 2026-03-18
**Overall Confidence:** HIGH

## Recommended Stack

### Backend Core

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12+ | Runtime | Stable, full async support, best typing ergonomics. 3.13 is fine too but 3.12 is the safe floor. | HIGH |
| FastAPI | 0.135+ | Web framework | Async-native, built-in SSE support (new `fastapi.sse` module), Pydantic v2 integration, excellent DX. The dominant Python API framework. | HIGH |
| Pydantic | 2.12+ | Data validation/serialization | Required by FastAPI. V2 is 5-50x faster than v1. Use `BaseModel` for all request/response schemas. | HIGH |
| Uvicorn | 0.34+ | ASGI server | Standard FastAPI deployment server. Use `--reload` in dev. | HIGH |

### Database & ORM

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| SQLite | (system) | Database | Zero-config, file-based, perfect for single-user local app. No server process needed. | HIGH |
| SQLAlchemy | 2.0.48+ | ORM | The Python ORM standard. 2.0-style uses explicit `select()` statements -- more predictable than the legacy implicit query API. Full async support via `AsyncSession`. | HIGH |
| aiosqlite | 0.22+ | Async SQLite driver | Required bridge for SQLAlchemy async + SQLite. SQLAlchemy's async engine uses this under the hood with `sqlite+aiosqlite://` connection string. | HIGH |
| Alembic | 1.18+ | Database migrations | The only serious migration tool for SQLAlchemy. Run `alembic init` early; autogenerate migrations from model changes. Even for SQLite -- schema will evolve. | HIGH |

### Scraping

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Playwright | 1.58+ | Headless browser automation | Retailers (Amazon, Walmart, BestBuy) render prices via JavaScript. Static HTTP scraping will not work. Playwright's async Python API (`async_playwright`) integrates cleanly with FastAPI's async loop. Auto-waits for elements, handles anti-bot JS better than alternatives. | HIGH |

### Scheduling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| APScheduler | 3.11+ | Background job scheduling | Embedded in-process scheduler -- no Redis, no Celery, no external broker. Use `AsyncIOScheduler` to run on the same event loop as FastAPI. **Use v3.x, not v4.x** -- v4 is still pre-release/unstable as of March 2026. | HIGH |

### Real-Time Notifications

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| FastAPI SSE (built-in) | (included in FastAPI 0.135+) | Server-to-client push | FastAPI now has native SSE via `fastapi.sse.EventSourceResponse` and `ServerSentEvent`. No need for the `sse-starlette` third-party package. SSE is simpler than WebSockets for this use case: notifications are server-to-client only (unidirectional). | HIGH |

### Frontend Core

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| React | 19.2+ | UI framework | Stable, massive ecosystem, project requirement. | HIGH |
| TypeScript | 5.7+ | Type safety | Catches bugs at build time. Use strict mode. Non-negotiable for any project beyond a toy. | HIGH |
| Vite | 8.0+ | Build tool/dev server | 5x faster than webpack, native ESM, instant HMR. The standard React build tool in 2026 (Create React App is dead). Use `@vitejs/plugin-react` v6 (now uses Oxc instead of Babel -- faster builds). | HIGH |
| TanStack Query | 5.90+ | Server state management | Handles data fetching, caching, refetching, loading/error states. Eliminates manual `useEffect` + `useState` fetch patterns. The standard for server-state in React. | HIGH |

### Frontend UI & Styling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Tailwind CSS | 4.2+ | Utility-first CSS | v4 rewrote the engine -- 5x faster, CSS-native config (no `tailwind.config.js`). Reduces CSS decision fatigue. | HIGH |
| Recharts | 3.8+ | Price history charts | React-native, declarative, built on D3. `LineChart` component maps directly to the price-over-time visualization requirement. Simpler API than Chart.js/react-chartjs-2. | MEDIUM |
| Lucide React | latest | Icons | Clean, tree-shakeable icon set. Better maintained than react-icons (which bundles everything). | MEDIUM |

### Dev Tooling

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Ruff | latest | Python linting + formatting | Replaces both flake8 and black. Written in Rust, 10-100x faster. Single tool for lint + format. | HIGH |
| pytest | 8+ | Python testing | Standard. Use `pytest-asyncio` for async test functions. | HIGH |
| httpx | 0.28+ | HTTP test client | FastAPI's recommended test client (`from httpx import AsyncClient`). Async-native unlike `requests`. | HIGH |

## Key Integration Patterns

### FastAPI + APScheduler Lifecycle

```python
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
```

Use FastAPI's `lifespan` context manager (not deprecated `on_event`). The scheduler shares the asyncio event loop with FastAPI.

### SQLAlchemy Async Session with FastAPI

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine("sqlite+aiosqlite:///./prices.db")
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
```

Use FastAPI's `Depends(get_db)` for dependency injection. `expire_on_commit=False` prevents lazy-load issues after commit in async context.

### Playwright Async Usage

```python
from playwright.async_api import async_playwright

async def scrape_price(url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        # Extract price with page.locator() or page.eval_on_selector()
        await browser.close()
```

**Performance note:** Launching a browser per scrape is expensive. For production, maintain a persistent browser instance and create new pages (tabs) per scrape. Close pages after each scrape to prevent memory leaks.

### SSE for Notifications (FastAPI Native)

```python
from fastapi.sse import EventSourceResponse, ServerSentEvent

@app.get("/notifications/stream")
async def notification_stream():
    async def event_generator():
        while True:
            # Check for new alerts (from DB or in-memory queue)
            notification = await get_next_notification()
            if notification:
                yield ServerSentEvent(data=notification.json(), event="price_alert")
            await asyncio.sleep(1)
    return EventSourceResponse(event_generator())
```

On the React side, use the native `EventSource` API or a lightweight wrapper.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| ORM | SQLAlchemy 2.0 | Tortoise ORM | Tortoise is async-first but smaller ecosystem, less mature migrations (Aerich vs Alembic), fewer resources/examples. SQLAlchemy is the industry standard. |
| ORM | SQLAlchemy 2.0 | Raw SQL / aiosqlite directly | Loses migration tooling, schema validation, and relationship management. Not worth the "simplicity" trade-off. |
| Scheduler | APScheduler 3.x | APScheduler 4.x | v4 is still not production-ready (March 2026). The API changed significantly and the `fastapi-apscheduler4` wrapper explicitly warns against production use. Stick with 3.x. |
| Scheduler | APScheduler 3.x | Celery + Redis | Massive overkill for a single-user local app. Requires Redis broker, separate worker process. APScheduler embeds in the FastAPI process. |
| Notifications | SSE | WebSockets | WebSockets are bidirectional -- unnecessary complexity for server-to-client-only notifications. SSE auto-reconnects, works over standard HTTP, and FastAPI now has native support. |
| Notifications | SSE | Polling | Wastes resources. SSE is a persistent connection with instant push. Polling adds latency and unnecessary DB queries. |
| Charts | Recharts | Chart.js (react-chartjs-2) | Chart.js uses canvas (not SVG), harder to customize with React patterns. Recharts is declarative and React-native. |
| Charts | Recharts | Nivo | Nivo is more powerful but heavier. Recharts is simpler for line charts, which is the primary use case here. |
| Build tool | Vite | webpack | webpack is slower, more complex config, legacy. Vite is the standard in 2026. |
| CSS | Tailwind 4 | CSS Modules / styled-components | Tailwind is faster to develop with for dashboard UIs. styled-components has runtime cost. CSS Modules are fine but slower developer velocity. |
| State mgmt | TanStack Query | Redux / Zustand | This app's state is almost entirely server-derived (prices, alerts, watch queries). TanStack Query is purpose-built for this. Redux/Zustand are for complex client-side state, which this app has very little of. |
| Formatting | Ruff | Black + flake8 + isort | Ruff replaces all three in a single, faster tool. No reason to use the old trio anymore. |

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| APScheduler 4.x | Not production-ready. API unstable, core lib still in pre-release. |
| `sse-starlette` | FastAPI 0.135+ has built-in SSE. No need for the third-party package anymore. |
| `requests` library | Synchronous. Will block the FastAPI event loop. Use `httpx` if you need an HTTP client. |
| Create React App | Deprecated, unmaintained. Use Vite. |
| Flask | No async support without hacks. FastAPI is strictly better for this use case. |
| BeautifulSoup / Scrapy | These are for static HTML scraping. Retailers render prices with JavaScript; only a headless browser (Playwright) works. |
| `fastapi.on_event("startup")` | Deprecated. Use the `lifespan` context manager pattern instead. |
| SQLAlchemy 1.x query API | The `session.query(Model)` style is legacy. Use `select(Model)` statements (2.0 style). |

## Installation

### Backend

```bash
# Core
pip install "fastapi[standard]" uvicorn sqlalchemy[asyncio] aiosqlite alembic pydantic apscheduler playwright

# Install Playwright browsers (one-time)
playwright install chromium

# Dev dependencies
pip install pytest pytest-asyncio httpx ruff
```

### Frontend

```bash
# Scaffold with Vite
npm create vite@latest frontend -- --template react-ts

cd frontend

# Core
npm install @tanstack/react-query recharts

# Styling
npm install -D tailwindcss @tailwindcss/vite

# Dev tooling (included with Vite scaffold)
# TypeScript, ESLint already configured
```

### Project Structure

```
price_scraper/
  backend/
    app/
      __init__.py
      main.py            # FastAPI app, lifespan, CORS
      config.py           # Settings via pydantic-settings
      database.py         # Engine, session factory
      models/             # SQLAlchemy models
      schemas/            # Pydantic request/response schemas
      routers/            # API route modules
      services/           # Business logic (scraping, scheduling, alerts)
    alembic/              # Migration scripts
    alembic.ini
    requirements.txt
    prices.db             # SQLite file (gitignored)
  frontend/
    src/
      components/         # React components
      hooks/              # Custom hooks (useQueries, useSSE)
      pages/              # Dashboard, WatchQueryDetail
      api/                # API client functions
      types/              # TypeScript interfaces
    index.html
    vite.config.ts
    tailwind.css
```

## Version Pinning Strategy

Pin major + minor, allow patch updates. Example `requirements.txt`:

```
fastapi>=0.135,<1.0
sqlalchemy>=2.0.48,<2.1
aiosqlite>=0.22,<1.0
alembic>=1.18,<2.0
pydantic>=2.12,<3.0
apscheduler>=3.11,<4.0
playwright>=1.58,<2.0
uvicorn>=0.34,<1.0
```

For frontend, use `package-lock.json` (auto-generated by npm) for reproducible installs.

## Sources

- [FastAPI Release Notes](https://fastapi.tiangolo.com/release-notes/) - Version and SSE feature verification
- [FastAPI SSE Documentation](https://fastapi.tiangolo.com/tutorial/server-sent-events/) - Native SSE support
- [SQLAlchemy 2.0 Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) - Async SQLite patterns
- [SQLAlchemy PyPI](https://pypi.org/project/SQLAlchemy/) - Version 2.0.48
- [Alembic Documentation](https://alembic.sqlalchemy.org/) - Version 1.18.4
- [aiosqlite PyPI](https://pypi.org/project/aiosqlite/) - Version 0.22.1
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) - Version 3.11.2, v4 not production-ready
- [fastapi-apscheduler4 PyPI](https://pypi.org/project/fastapi-apscheduler4/) - Confirms v4 not production-ready
- [Playwright Python Release Notes](https://playwright.dev/python/docs/release-notes) - Version 1.58
- [Pydantic PyPI](https://pypi.org/project/pydantic/) - Version 2.12.5 stable
- [Vite 8.0 Announcement](https://vite.dev/blog/announcing-vite8) - Vite 8 with Rolldown
- [React 19.2 Release](https://react.dev/blog/2025/10/01/react-19-2) - React 19.2.4
- [TanStack Query](https://tanstack.com/query/latest) - v5.90+
- [Recharts GitHub](https://github.com/recharts/recharts) - v3.8.0
- [Tailwind CSS v4.2](https://tailwindcss.com/blog) - v4.2.0
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) - Compared against native FastAPI SSE
