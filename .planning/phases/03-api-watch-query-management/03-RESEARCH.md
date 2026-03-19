# Phase 3: API + Watch Query Management - Research

**Researched:** 2026-03-18
**Domain:** FastAPI REST API, Pydantic validation, async CRUD endpoints, on-demand scrape triggering
**Confidence:** HIGH

## Summary

Phase 3 builds FastAPI REST endpoints on top of an already-complete data layer (Phase 1) and scraping engine (Phase 2). The repository layer, Pydantic schemas, scrape service, and BrowserManager all exist and are tested. The work is primarily wiring -- connecting existing async repository functions to HTTP route handlers, adding CORS middleware, extending schemas for embedded scrape results, and implementing URL deduplication logic.

The project uses FastAPI 0.135.1 with Pydantic 2.12.5, async SQLAlchemy sessions via `Depends(get_db)`, and the established pattern of `flush()` in repos with `commit()` handled by the DI session context manager. All endpoints will be async. The on-demand scrape endpoint is synchronous in the HTTP sense (awaits `run_scrape_job()` and returns results, not 202 Accepted).

**Primary recommendation:** Build two router modules (`watch_queries.py` and `scrapes.py`), mount them in `main.py` with CORS, extend existing schemas for embedded latest results and price deltas, and add URL deduplication as a simple `list(dict.fromkeys(urls))` operation at the schema or route level.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- On-demand scrape is synchronous -- POST /watch-queries/{id}/scrape awaits run_scrape_job() and returns completed results (HTTP 200, not 202)
- Returns full result set: all ScrapeResult records with product name, price_cents, retailer name, listing URL, and price delta vs previous
- BrowserManager initializes lazily on first scrape request (not in lifespan startup); subsequent requests reuse the shared instance
- GET /watch-queries/{id} returns watch query config AND the latest scrape result embedded per retailer URL (product_name, price_cents, listing_url, scraped_at, price delta direction)
- Price history endpoint: GET /retailer-urls/{id}/history -- all scrape results for a URL ordered newest-first
- History records include computed delta fields (direction, delta_cents, pct_change) server-side via calculate_price_delta()
- Duplicate URL handling: silent deduplication, exact string match (byte-for-byte), no normalization, applied at create and edit time
- Split routers: watch_queries.py (CRUD) and scrapes.py (scrape trigger + history)
- CORS locked to http://localhost:5173 and http://localhost:3000

### Claude's Discretion
- Exact BrowserManager singleton implementation (module-level instance vs app.state vs DI)
- Pydantic response schema for embedded latest_result on retailer URLs (extend RetailerUrlResponse or separate schema)
- Pagination on history endpoint (or not, given small personal dataset)
- Error response format for 404 and validation errors (FastAPI defaults are fine)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUERY-01 | User can create a watch query with a search term, one or more retailer URLs, and a price threshold | Existing `create_watch_query` repo + `WatchQueryCreate` schema; route handler wires POST endpoint with dedup |
| QUERY-02 | User can edit a watch query's name, price threshold, and retailer URLs | Existing `update_watch_query` repo + `WatchQueryUpdate` schema; needs URL replacement logic with dedup |
| QUERY-03 | User can delete a watch query | Existing `delete_watch_query` repo with cascade; route returns 204 |
| QUERY-04 | User can pause and resume a watch query (paused queries skip scheduled scrapes but retain config) | Existing `update_watch_query` supports `is_active` field; PATCH endpoint toggles it |
| QUERY-05 | System identifies and filters duplicate retailer URLs within a watch query at creation and edit time | Silent byte-for-byte dedup via `list(dict.fromkeys(urls))` before passing to repo |
| SCRAPE-03 | User can trigger an on-demand scrape for any watch query from the UI | POST endpoint calls `run_scrape_job()` with lazy-init BrowserManager, returns full results with deltas |

</phase_requirements>

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.1 | Web framework, routing, DI | Already in use; async-first, Pydantic-native |
| Pydantic | 2.12.5 | Request/response validation | Already in use; `model_config = ConfigDict(from_attributes=True)` for ORM mode |
| SQLAlchemy | 2.0.x (async) | ORM, async session | Already in use; established repository pattern |
| httpx | 0.28.1 | Test client for FastAPI | Already in dev deps; `AsyncClient` with `ASGITransport` for async test routes |
| pytest | 8.x | Test runner | Already configured with `asyncio_mode = "auto"` |
| pytest-asyncio | 0.24.x | Async test support | Already configured |

### Supporting (No New Packages Needed)
No additional packages are required. FastAPI includes `CORSMiddleware` in `fastapi.middleware.cors`. All route testing uses httpx `AsyncClient` already in dev dependencies.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Module-level BrowserManager | app.state on FastAPI | app.state is cleaner for lifecycle but module-level is simpler for this single-user tool |
| No pagination on history | cursor-based pagination | Overkill for personal tool with small datasets; add later if needed |

**Installation:**
```bash
# No new packages needed -- all dependencies already installed
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/api/
  __init__.py
  watch_queries.py     # CRUD: GET list, GET detail, POST create, PATCH update, DELETE
  scrapes.py           # POST /watch-queries/{id}/scrape, GET /retailer-urls/{id}/history
backend/app/schemas/
  watch_query.py       # Extend with ScrapeResultResponse, RetailerUrlWithLatest, ScrapeJobResponse
```

### Pattern 1: Route Handler Structure
**What:** Thin route handlers that delegate to repository functions, with session commit handled by DI
**When to use:** Every endpoint in this phase
**Example:**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.watch_query import get_watch_query, create_watch_query

router = APIRouter(prefix="/watch-queries", tags=["watch-queries"])

@router.post("/", response_model=WatchQueryResponse, status_code=201)
async def create(payload: WatchQueryCreate, db: AsyncSession = Depends(get_db)):
    # Deduplicate URLs (QUERY-05)
    unique_urls = list(dict.fromkeys(payload.urls))
    query = await create_watch_query(db, name=payload.name, threshold_cents=payload.threshold_cents, urls=unique_urls)
    return query
```

### Pattern 2: BrowserManager Lazy Singleton
**What:** Module-level BrowserManager instance, initialized lazily on first scrape request
**When to use:** On-demand scrape endpoint
**Example:**
```python
# backend/app/api/scrapes.py
from app.scrapers.browser import BrowserManager

_browser_manager: BrowserManager | None = None

async def get_browser_manager() -> BrowserManager:
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
        await _browser_manager.start()
    return _browser_manager
```

### Pattern 3: URL Replacement on Update
**What:** When URLs are provided in PATCH, delete existing RetailerUrl rows and create new ones (with dedup)
**When to use:** PATCH /watch-queries/{id} when `urls` field is present
**Example:**
```python
# In watch_query repository or route handler:
if payload.urls is not None:
    unique_urls = list(dict.fromkeys(payload.urls))
    # Delete existing retailer URLs
    for url_obj in query.retailer_urls:
        await db.delete(url_obj)
    await db.flush()
    # Create new ones
    query.retailer_urls = [RetailerUrl(url=u, watch_query_id=query.id) for u in unique_urls]
    await db.flush()
```

### Pattern 4: Embedded Latest Result in GET Detail
**What:** GET /watch-queries/{id} returns each RetailerUrl with its latest ScrapeResult and price delta
**When to use:** Watch query detail endpoint
**Example:**
```python
class LatestScrapeResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_name: str
    price_cents: int
    listing_url: str
    scraped_at: datetime
    direction: str       # "new" | "higher" | "lower" | "unchanged"
    delta_cents: int
    pct_change: float

class RetailerUrlWithLatest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    url: str
    created_at: datetime
    latest_result: LatestScrapeResult | None = None
```

### Pattern 5: CORS Middleware Configuration
**What:** Add CORSMiddleware to FastAPI app in main.py
**When to use:** Once, in app initialization
**Example:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Anti-Patterns to Avoid
- **Committing inside route handlers:** The `get_db` dependency already commits on success and rolls back on exception. Route handlers must NOT call `session.commit()`.
- **Blocking scrape in a sync function:** All route handlers and the scrape service are async. Do not use `asyncio.run()` or `run_in_executor()`.
- **Returning ORM objects without `from_attributes=True`:** All response schemas must use `ConfigDict(from_attributes=True)` to serialize SQLAlchemy models.
- **Normalizing URLs when deduplicating:** Decision explicitly says byte-for-byte match only. Do not strip trailing slashes, lowercase, or parse URLs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CORS handling | Custom headers/middleware | `fastapi.middleware.cors.CORSMiddleware` | Handles preflight OPTIONS, varies by origin, handles credentials |
| Request validation | Manual type checking | Pydantic schemas with `field_validator` | Already in place; automatic 422 responses with details |
| 404 responses | Custom exception handling | `raise HTTPException(status_code=404, detail="...")` | FastAPI standard pattern, consistent error format |
| URL deduplication | Set-based dedup (loses order) | `list(dict.fromkeys(urls))` | Preserves insertion order, removes duplicates, one-liner |
| Test client | Manual HTTP calls | `httpx.AsyncClient(transport=ASGITransport(app=app))` | FastAPI recommended async testing approach |
| Session lifecycle | Manual open/commit/close | `Depends(get_db)` | Already handles commit/rollback; established pattern |

**Key insight:** This phase has zero new library requirements. Every tool needed is already installed and patterned. The work is purely wiring existing pieces together.

## Common Pitfalls

### Pitfall 1: Lazy-loaded Relationships Not Available
**What goes wrong:** Accessing `watch_query.retailer_urls` outside of the session scope raises `MissingGreenlet` error.
**Why it happens:** SQLAlchemy async mode requires explicit eager loading; lazy loading is not supported.
**How to avoid:** Always use `selectinload(WatchQuery.retailer_urls)` in queries (already done in `get_watch_query` and `list_watch_queries`). For the scrape endpoint, ensure the query includes `selectinload` for retailer URLs and their scrape results.
**Warning signs:** `MissingGreenlet` or `DetachedInstanceError` in route responses.

### Pitfall 2: URL Replacement Cascade Conflicts
**What goes wrong:** Deleting RetailerUrl objects that have ScrapeResult children can trigger cascade deletes of historical data.
**Why it happens:** `RetailerUrl.scrape_results` has `cascade="all, delete-orphan"`. Deleting a RetailerUrl deletes its scrape history.
**How to avoid:** When updating URLs, only remove RetailerUrl objects whose URLs are no longer in the new list. Add new ones. Do not blindly delete-all-and-recreate if preserving history matters. However, per the current design decision for this personal tool, full replacement may be acceptable -- the planner should decide based on whether Phase 6 (history charts) needs historical data for removed URLs.
**Warning signs:** Missing scrape history after editing a watch query's URLs.

### Pitfall 3: BrowserManager Not Cleaned Up
**What goes wrong:** Browser processes leak if the app shuts down without calling `browser_manager.stop()`.
**Why it happens:** Lazy initialization means the browser is not tied to FastAPI's lifespan.
**How to avoid:** Register a shutdown handler in the FastAPI lifespan that checks if the module-level BrowserManager was initialized and calls `stop()` on it.
**Warning signs:** Orphaned Chrome processes after app restart.

### Pitfall 4: Scrape Endpoint Timeout
**What goes wrong:** On-demand scrape for a watch query with many URLs takes too long, client times out.
**Why it happens:** Synchronous await of sequential URL scraping (each URL can take 5-30s with retries).
**How to avoid:** For this personal tool with small URL counts, this is acceptable. Document that a watch query with 10+ URLs may take minutes. Uvicorn default timeout is 60s; consider increasing if needed.
**Warning signs:** HTTP 502/504 errors on scrape trigger.

### Pitfall 5: Pydantic Validation Errors on Nested ORM Objects
**What goes wrong:** Response serialization fails when ORM relationships contain unexpected None values or missing attributes.
**Why it happens:** Schema expects fields that the ORM model does not populate (e.g., computed delta fields not on the model).
**How to avoid:** Build response dictionaries manually for computed fields (price deltas) rather than relying on `from_attributes=True` alone. Use a service function to assemble the complete response data.
**Warning signs:** 500 errors on GET endpoints that worked for simple cases.

## Code Examples

### Router Registration in main.py
```python
# backend/main.py
from app.api.watch_queries import router as watch_queries_router
from app.api.scrapes import router as scrapes_router

app.include_router(watch_queries_router)
app.include_router(scrapes_router)
```

### Async Test Client Setup
```python
# tests/conftest.py (addition)
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.core.database import get_db
from backend.main import app

@pytest_asyncio.fixture
async def client(db_session):
    """Provide an async test client with overridden DB dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

### Scrape Results with Deltas (Response Assembly)
```python
async def build_scrape_response(session, job, retailer_urls):
    """Build response with scrape results and price deltas."""
    results = []
    for url_obj in retailer_urls:
        # Get results for this job
        stmt = select(ScrapeResult).where(
            ScrapeResult.scrape_job_id == job.id,
            ScrapeResult.retailer_url_id == url_obj.id,
        )
        result = await session.execute(stmt)
        scrape_result = result.scalar_one_or_none()
        if scrape_result:
            delta = await calculate_price_delta(
                session, url_obj.id, scrape_result.price_cents
            )
            results.append({
                "product_name": scrape_result.product_name,
                "price_cents": scrape_result.price_cents,
                "retailer_name": scrape_result.retailer_name,
                "listing_url": scrape_result.listing_url,
                "scraped_at": scrape_result.created_at,
                **delta,
            })
    return results
```

### History Endpoint with Deltas
```python
@router.get("/retailer-urls/{retailer_url_id}/history")
async def get_history(retailer_url_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(ScrapeResult)
        .where(ScrapeResult.retailer_url_id == retailer_url_id)
        .order_by(ScrapeResult.created_at.desc(), ScrapeResult.id.desc())
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())
    # Compute deltas between consecutive records
    # Each record's delta is vs the record that came before it chronologically
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `TestClient` (sync) | `httpx.AsyncClient` with `ASGITransport` | FastAPI 0.100+ | Must use async client for async route testing |
| Pydantic v1 `orm_mode=True` | Pydantic v2 `ConfigDict(from_attributes=True)` | Pydantic 2.0 | Already in use in schemas |
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93+ | Already in use in main.py |

**Deprecated/outdated:**
- `TestClient` from Starlette: Still works for sync but cannot test async dependencies properly. Use `httpx.AsyncClient`.
- `response_model_exclude_unset`: Still valid but prefer explicit schema design over exclusion flags.

## Open Questions

1. **URL Replacement vs URL Diff on Edit**
   - What we know: RetailerUrl has cascade delete-orphan to ScrapeResult. Full URL replacement deletes scrape history for removed URLs.
   - What's unclear: Whether preserving history for removed URLs matters at this stage (Phase 6 builds history charts).
   - Recommendation: Use diff-based approach (only delete removed URLs, add new ones) to preserve history. Safer default that does not destroy data.

2. **BrowserManager Cleanup on Shutdown**
   - What we know: Lazy init means browser is not part of lifespan.
   - What's unclear: Whether the lifespan can access the module-level singleton reliably.
   - Recommendation: Add cleanup in lifespan's `yield` teardown section by importing and checking the module-level instance.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]` with `asyncio_mode = "auto"`) |
| Quick run command | `cd backend && python -m pytest tests/api/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUERY-01 | POST /watch-queries/ creates query with URLs and threshold | integration | `cd backend && python -m pytest tests/api/test_watch_queries.py::test_create_watch_query -x` | No -- Wave 0 |
| QUERY-02 | PATCH /watch-queries/{id} updates name, threshold, URLs | integration | `cd backend && python -m pytest tests/api/test_watch_queries.py::test_update_watch_query -x` | No -- Wave 0 |
| QUERY-03 | DELETE /watch-queries/{id} returns 204 | integration | `cd backend && python -m pytest tests/api/test_watch_queries.py::test_delete_watch_query -x` | No -- Wave 0 |
| QUERY-04 | PATCH is_active toggles pause/resume | integration | `cd backend && python -m pytest tests/api/test_watch_queries.py::test_pause_resume -x` | No -- Wave 0 |
| QUERY-05 | Duplicate URLs silently deduplicated at create and edit | integration | `cd backend && python -m pytest tests/api/test_watch_queries.py::test_dedup_urls -x` | No -- Wave 0 |
| SCRAPE-03 | POST /watch-queries/{id}/scrape returns results with deltas | integration | `cd backend && python -m pytest tests/api/test_scrapes.py::test_trigger_scrape -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/api/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/api/__init__.py` -- package init
- [ ] `tests/api/test_watch_queries.py` -- CRUD endpoint tests (QUERY-01 through QUERY-05)
- [ ] `tests/api/test_scrapes.py` -- scrape trigger and history endpoint tests (SCRAPE-03)
- [ ] `tests/conftest.py` -- add `client` fixture using `httpx.AsyncClient` with `ASGITransport` and DB dependency override

## Sources

### Primary (HIGH confidence)
- Direct code inspection of existing codebase: models, schemas, repositories, services, browser manager, main.py, conftest.py
- Installed package versions verified via `pip show`: FastAPI 0.135.1, Pydantic 2.12.5, httpx 0.28.1
- FastAPI CORSMiddleware is part of the framework (no external package needed)

### Secondary (MEDIUM confidence)
- FastAPI async testing pattern with `httpx.AsyncClient` + `ASGITransport` -- standard documented approach since FastAPI 0.100+
- `list(dict.fromkeys())` for order-preserving deduplication -- Python 3.7+ guaranteed dict insertion order

### Tertiary (LOW confidence)
- None -- all findings verified against existing code and installed packages

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages already installed and in use; no new dependencies
- Architecture: HIGH -- patterns established in Phase 1/2; this phase extends them with route handlers
- Pitfalls: HIGH -- identified from direct code inspection of cascade relationships and async patterns

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable -- no fast-moving dependencies)
