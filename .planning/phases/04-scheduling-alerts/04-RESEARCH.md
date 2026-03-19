# Phase 4: Scheduling + Alerts - Research

**Researched:** 2026-03-18
**Domain:** Background job scheduling (APScheduler), alert evaluation, Server-Sent Events (SSE)
**Confidence:** HIGH

## Summary

Phase 4 implements the automated scrape-evaluate-alert-push loop. Three main technical domains are involved: (1) APScheduler 3.x AsyncIOScheduler for running per-query scrape jobs on configurable intervals, (2) alert evaluation logic that checks scrape results against thresholds with re-breach detection, and (3) FastAPI's built-in SSE support for pushing alert notifications to connected browser clients.

The existing codebase provides strong foundations: the Alert model already exists, `run_scrape_job()` handles scrape orchestration, `async_session_factory` provides DB sessions outside request context, and the FastAPI lifespan hook is ready for scheduler integration. The WatchQuery model already has a `schedule` field (String, default "daily").

**Primary recommendation:** Use APScheduler 3.11.x AsyncIOScheduler with MemoryJobStore (jobs rebuilt from DB on startup), FastAPI built-in `fastapi.sse.EventSourceResponse` for SSE (no external dependency needed since FastAPI >= 0.135.0), and an `asyncio.Queue`-per-client pattern for broadcasting alert events.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Alert fires only on **first breach** -- when price drops to/below threshold for the first time (per retailer URL). No repeat alert while price stays at or below threshold across subsequent scrapes. A **new alert fires on re-breach**: if price rises above threshold and then drops back below, that is treated as a new breach.
- **One alert record per scrape result that breaches threshold** -- not one per job. If 3 retailer URLs below threshold, 3 separate Alert records are created (each linked to ScrapeResult via scrape_result_id).
- **Skip missed scrapes** on startup -- do not run immediately; wait for next scheduled interval. Auto-register all non-paused watch queries during FastAPI lifespan startup. Job IDs keyed by watch_query_id for cancel/update.
- SSE stream pushes **alert events only** -- no scrape job status events. Full detail payload per alert event: alert_id, watch_query_id, watch_query_name, product_name, price_cents, retailer_name, listing_url, created_at, unread_count.

### Claude's Discretion
- APScheduler job store (MemoryJobStore vs SQLAlchemyJobStore) -- MemoryJobStore is fine since jobs are always rebuilt from DB on startup
- Exact APScheduler scheduler type (AsyncIOScheduler vs BackgroundScheduler with asyncio bridge)
- SSE connection management implementation (asyncio.Queue per client, generator pattern)
- Alert evaluation: inline within run_scrape_job (after each result is stored) or as a post-job pass
- Exact re-breach detection query structure

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCRAPE-02 | Scraping runs automatically on a per-query configurable schedule (every 6h, 12h, daily, or weekly) as a background job | APScheduler AsyncIOScheduler with IntervalTrigger; schedule mapping from WatchQuery.schedule string to interval kwargs |
| ALERT-01 | System triggers an alert record when a scraped price is at or below the watch query's configured threshold | Alert evaluation service checks `price_cents <= threshold_cents` with re-breach detection query; Alert model already exists |
| ALERT-02 | In-app notification badge on the nav shows unread alert count; a toast appears when new alerts arrive | FastAPI built-in SSE (`fastapi.sse.EventSourceResponse`); asyncio.Queue per connected client; alert event payload includes unread_count |
| ALERT-03 | User can view an alert log showing all triggered alerts (query name, product name, price, retailer, timestamp) | Alert repository with joined query on ScrapeResult + WatchQuery; paginated list endpoint |
| ALERT-04 | User can mark individual alerts as read and dismiss all alerts at once; badge count reflects unread only | PATCH /alerts/{id}/read, POST /alerts/dismiss-all endpoints; unread count query for badge |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.11.2 | Background job scheduling | Only embedded Python scheduler with async support; locked project constraint |
| FastAPI (built-in SSE) | >=0.135.0 | Server-Sent Events | Native `fastapi.sse.EventSourceResponse` -- no external dependency needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy (existing) | >=2.0.48 | Alert repository queries | Already in project; used for re-breach detection queries |
| Pydantic (existing) | v2 | Alert schemas | Already in project; response/request validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI built-in SSE | sse-starlette 3.3.3 | External dep; FastAPI native is sufficient and simpler |
| MemoryJobStore | SQLAlchemyJobStore | Unnecessary -- jobs rebuilt from DB on startup; adds complexity |
| AsyncIOScheduler | BackgroundScheduler | BackgroundScheduler runs in separate thread, needs bridge to asyncio; AsyncIOScheduler runs natively in the event loop |

**Discretion recommendation:** Use **AsyncIOScheduler** (shares FastAPI's event loop, no threading complexity) with **MemoryJobStore** (default, simplest, appropriate since jobs are rebuilt from DB on startup).

**Installation:**
```bash
pip install "APScheduler>=3.11.0,<4.0"
```

Add to pyproject.toml dependencies:
```toml
"APScheduler>=3.11.0,<4.0",
```

Also update FastAPI minimum version in pyproject.toml to ensure SSE support:
```toml
"fastapi>=0.135.0",
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  services/
    scheduler.py         # Scheduler singleton, schedule mapping, job registration
    alert_service.py     # Alert evaluation, re-breach detection, SSE broadcast
  api/
    alerts.py            # Alert CRUD endpoints + SSE stream endpoint
  repositories/
    alert.py             # Alert DB queries (create, list, mark read, count unread)
  schemas/
    alert.py             # Alert Pydantic schemas (response, SSE event payload)
```

### Pattern 1: Scheduler Singleton Module
**What:** A module-level scheduler instance that can be imported by both lifespan (for start/stop) and route handlers (for dynamic job add/remove).
**When to use:** When multiple parts of the app need to interact with the scheduler.
**Example:**
```python
# backend/app/services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Module-level singleton
scheduler = AsyncIOScheduler()

SCHEDULE_MAP = {
    "every_6h": {"hours": 6},
    "every_12h": {"hours": 12},
    "daily": {"days": 1},
    "weekly": {"weeks": 1},
}

async def register_jobs_from_db():
    """Load all active watch queries and register their scrape jobs."""
    from app.core.database import async_session_factory
    from app.models.watch_query import WatchQuery
    from sqlalchemy import select

    async with async_session_factory() as session:
        stmt = select(WatchQuery).where(WatchQuery.is_active == True)
        result = await session.execute(stmt)
        queries = result.scalars().all()

    for query in queries:
        add_scrape_job(query.id, query.schedule)

def add_scrape_job(watch_query_id: int, schedule: str):
    """Add or replace a scheduled scrape job for a watch query."""
    job_id = f"scrape_query_{watch_query_id}"
    interval_kwargs = SCHEDULE_MAP.get(schedule, {"days": 1})

    # Remove existing job if present (handles reschedule)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        scheduled_scrape,
        trigger="interval",
        id=job_id,
        **interval_kwargs,
        misfire_grace_time=60,  # skip if missed by > 60s
        replace_existing=True,
    )

def remove_scrape_job(watch_query_id: int):
    """Remove a scheduled scrape job."""
    job_id = f"scrape_query_{watch_query_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

async def scheduled_scrape(watch_query_id: int):
    """The actual job function invoked by APScheduler."""
    from app.core.database import async_session_factory
    from app.scrapers.browser import BrowserManager
    from app.services.scrape_service import run_scrape_job

    # Reuse the lazy BrowserManager from scrapes module
    from app.api.scrapes import get_browser_manager
    bm = await get_browser_manager()

    async with async_session_factory() as session:
        try:
            job = await run_scrape_job(session, watch_query_id, bm)
            # Alert evaluation happens here or inside run_scrape_job
            await evaluate_alerts(session, watch_query_id, job.id)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Pattern 2: SSE Client Manager with asyncio.Queue
**What:** Each connected SSE client gets an `asyncio.Queue`. Alert service broadcasts to all queues. Disconnected clients are cleaned up.
**When to use:** When multiple browser tabs/clients may be connected simultaneously.
**Example:**
```python
# backend/app/services/alert_service.py
import asyncio
from typing import Any

# Set of asyncio.Queue instances, one per connected SSE client
_sse_clients: set[asyncio.Queue] = set()

def add_sse_client(queue: asyncio.Queue) -> None:
    _sse_clients.add(queue)

def remove_sse_client(queue: asyncio.Queue) -> None:
    _sse_clients.discard(queue)

async def broadcast_alert(event_data: dict[str, Any]) -> None:
    """Push alert event to all connected SSE clients."""
    for queue in _sse_clients.copy():
        try:
            queue.put_nowait(event_data)
        except asyncio.QueueFull:
            pass  # Client is slow; drop the event

# SSE endpoint
# backend/app/api/alerts.py
from fastapi import Request
from fastapi.sse import EventSourceResponse, ServerSentEvent

@router.get("/alerts/stream")
async def alert_stream(request: Request):
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    add_sse_client(queue)
    try:
        async def event_generator():
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield ServerSentEvent(data=data, event="alert")
                except asyncio.TimeoutError:
                    continue  # Keep-alive handled by FastAPI
        return EventSourceResponse(event_generator())
    finally:
        remove_sse_client(queue)
```

### Pattern 3: Re-breach Detection Query
**What:** Before creating an alert, check if the previous scrape result for this retailer URL was already below threshold. If so, this is a continued breach (skip). If the previous was above threshold (or no previous alert exists), this is a new/re-breach (fire alert).
**When to use:** On every scrape result that is at or below threshold.
**Example:**
```python
async def should_fire_alert(
    session: AsyncSession,
    retailer_url_id: int,
    watch_query_id: int,
    current_price_cents: int,
    threshold_cents: int,
) -> bool:
    """Return True if this is a new breach (not a continued breach)."""
    if current_price_cents > threshold_cents:
        return False

    # Get the previous scrape result (before the current one) for this retailer URL
    stmt = (
        select(ScrapeResult)
        .where(ScrapeResult.retailer_url_id == retailer_url_id)
        .order_by(ScrapeResult.created_at.desc(), ScrapeResult.id.desc())
        .offset(1)  # Skip the current result (just flushed)
        .limit(1)
    )
    result = await session.execute(stmt)
    previous = result.scalar_one_or_none()

    if previous is None:
        return True  # First-ever scrape; this is a new breach

    # If previous was also at or below threshold, this is a continued breach -- skip
    if previous.price_cents <= threshold_cents:
        return False

    # Previous was above threshold, current is at or below -- new breach
    return True
```

### Pattern 4: Lifespan Integration
**What:** Start scheduler during FastAPI startup, stop during shutdown.
**Example:**
```python
# backend/main.py -- updated lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    # Start scheduler and register jobs from DB
    from app.services.scheduler import scheduler, register_jobs_from_db
    await register_jobs_from_db()
    scheduler.start()

    yield

    # Shutdown scheduler
    scheduler.shutdown(wait=False)

    # Cleanup browser manager
    from app.api.scrapes import _browser_manager
    if _browser_manager is not None:
        await _browser_manager.stop()
```

### Anti-Patterns to Avoid
- **Starting scheduler before registering jobs:** Register jobs first, then call `scheduler.start()`. If started first, jobs registered immediately may fire before the app is fully initialized.
- **Using `coalesce=True` with `misfire_grace_time=None`:** This runs all missed jobs on startup, violating the "skip missed scrapes" decision. Use `misfire_grace_time=60` (or a small value) to skip missed fires.
- **Committing inside repository functions:** The project uses flush-not-commit discipline. Alert creation must follow: `session.add()` + `session.flush()`, with the caller owning `session.commit()`.
- **Creating DB sessions inside FastAPI route context via async_session_factory:** Routes use the `get_db` dependency. Only scheduler jobs (which run outside request context) should use `async_session_factory` directly.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron/interval scheduling | Custom asyncio.sleep loop | APScheduler IntervalTrigger | Handles drift, missed fires, timezone, job management |
| SSE protocol | Manual `text/event-stream` response | `fastapi.sse.EventSourceResponse` | Handles keep-alive pings, proper headers, disconnect detection |
| Job persistence across restarts | Custom DB-backed job store | MemoryJobStore + rebuild from DB | Jobs are cheap to rebuild; custom store adds complexity for no benefit |

**Key insight:** The scheduler is stateless (MemoryJobStore) because the source of truth for schedules is the WatchQuery table. Rebuilding on startup is simpler and more reliable than syncing two stores.

## Common Pitfalls

### Pitfall 1: Scheduler Job Function Must Accept Keyword Arguments
**What goes wrong:** APScheduler passes arguments to job functions via `args`/`kwargs` configured at `add_job` time. If you forget to pass `watch_query_id`, the job crashes silently.
**Why it happens:** `add_job` does not validate function signature at registration time.
**How to avoid:** Always pass `kwargs={"watch_query_id": id}` or use `functools.partial`. Test that jobs actually execute.
**Warning signs:** Jobs registered but never fire, or fire with `TypeError`.

### Pitfall 2: Session Lifecycle in Scheduler Jobs
**What goes wrong:** Scheduler jobs run outside FastAPI's request lifecycle, so there is no `get_db` dependency injection. If you forget to commit/rollback, changes are lost or connections leak.
**Why it happens:** `async_session_factory` creates raw sessions without the auto-commit/rollback wrapper.
**How to avoid:** Use `async with async_session_factory() as session:` with explicit `try/commit/except/rollback` pattern.
**Warning signs:** Alerts created in DB but not committed; connection pool exhaustion.

### Pitfall 3: SSE Generator Cleanup on Disconnect
**What goes wrong:** If the SSE generator does not clean up the client queue on disconnect, the `_sse_clients` set grows unboundedly.
**Why it happens:** `finally` blocks in async generators may not run if the client disconnects abruptly.
**How to avoid:** Use `try/finally` in the endpoint function (not just the generator) to ensure `remove_sse_client` runs. Alternatively, check `request.is_disconnected()` in the generator loop.
**Warning signs:** Memory growth over time, `_sse_clients` set growing.

### Pitfall 4: Race Condition in Alert Evaluation
**What goes wrong:** If two scrape jobs for the same query run concurrently (e.g., manual trigger + scheduled), both might evaluate the same result as a "new breach" and create duplicate alerts.
**Why it happens:** The re-breach check queries the DB state before the other job has committed.
**How to avoid:** This is unlikely in practice (SQLite serializes writes, single-user tool), but adding a unique constraint on `(scrape_result_id)` in the Alert table prevents true duplicates. The existing model already has `scrape_result_id` as a column; adding `unique=True` would be a safeguard.
**Warning signs:** Duplicate alert entries for the same scrape result.

### Pitfall 5: APScheduler Event Loop Conflict
**What goes wrong:** APScheduler's AsyncIOScheduler must share the same event loop as FastAPI. If started before the loop is running, it crashes.
**Why it happens:** `scheduler.start()` tries to get the running event loop.
**How to avoid:** Call `scheduler.start()` inside the FastAPI lifespan (which runs within the event loop). Never start the scheduler at module import time.
**Warning signs:** `RuntimeError: no running event loop` at startup.

## Code Examples

### Schedule Mapping (Verified from WatchQuery.schedule field values)
```python
SCHEDULE_MAP = {
    "every_6h": {"hours": 6},
    "every_12h": {"hours": 12},
    "daily": {"days": 1},
    "weekly": {"weeks": 1},
}
```

### Alert Evaluation After Scrape (Inline Pattern)
```python
async def evaluate_alerts_for_job(
    session: AsyncSession,
    watch_query_id: int,
    scrape_job_id: int,
) -> list[Alert]:
    """Evaluate all scrape results from a job for threshold breaches."""
    from app.models.watch_query import WatchQuery

    # Load threshold
    wq = await session.get(WatchQuery, watch_query_id)
    if wq is None:
        return []

    # Get all results from this job
    stmt = select(ScrapeResult).where(ScrapeResult.scrape_job_id == scrape_job_id)
    result = await session.execute(stmt)
    results = result.scalars().all()

    alerts_created = []
    for sr in results:
        if await should_fire_alert(session, sr.retailer_url_id, watch_query_id,
                                     sr.price_cents, wq.threshold_cents):
            alert = Alert(
                scrape_result_id=sr.id,
                watch_query_id=watch_query_id,
            )
            session.add(alert)
            await session.flush()
            alerts_created.append(alert)

    return alerts_created
```

### Alert API Endpoints
```python
# GET /alerts -- list all alerts with joined data
# PATCH /alerts/{alert_id}/read -- mark single alert as read
# POST /alerts/dismiss-all -- mark all unread alerts as read
# GET /alerts/unread-count -- get current unread count
# GET /alerts/stream -- SSE endpoint for real-time notifications
```

### Route Handler Notifying Scheduler on Pause/Delete
```python
# In watch_queries.py -- after updating is_active or deleting
from app.services.scheduler import add_scrape_job, remove_scrape_job

# On pause (is_active=False):
remove_scrape_job(query.id)

# On resume (is_active=True):
add_scrape_job(query.id, query.schedule)

# On delete:
remove_scrape_job(query_id)

# On schedule change:
add_scrape_job(query.id, query.schedule)  # replaces existing
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sse-starlette external lib | FastAPI built-in `fastapi.sse` | FastAPI 0.135.0 (March 2026) | No external dependency needed for SSE |
| APScheduler 4.x alpha | APScheduler 3.11.x stable | 4.x still alpha (4.0.0a6, Apr 2025) | Use 3.x; 4.x is not production-ready |

**Deprecated/outdated:**
- APScheduler 4.x: Still in alpha after years of development. Stick with 3.x for production use.
- sse-starlette: Still maintained (3.3.3), but unnecessary now that FastAPI has built-in SSE.

## Open Questions

1. **SSE endpoint cleanup under FastAPI built-in SSE**
   - What we know: FastAPI's `EventSourceResponse` handles keep-alive and basic disconnect detection
   - What's unclear: Whether `finally` blocks in async generators reliably run on client disconnect with the built-in implementation (sse-starlette had explicit disconnect detection)
   - Recommendation: Test disconnect behavior during implementation; fall back to sse-starlette if cleanup is unreliable

2. **BrowserManager sharing between route handlers and scheduler**
   - What we know: `_browser_manager` is a module-level singleton in `app.api.scrapes`; scheduler jobs need access to it
   - What's unclear: Whether importing from `app.api.scrapes` creates circular import issues when called from `scheduler.py`
   - Recommendation: Move `get_browser_manager()` to a shared services module if circular imports occur, or use lazy imports in the scheduler job function

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && python -m pytest tests/ -x -q --timeout=10` |
| Full suite command | `cd backend && python -m pytest tests/ -q --timeout=30` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCRAPE-02 | Scheduled scrape job fires on interval | unit | `cd backend && python -m pytest tests/services/test_scheduler.py -x` | No -- Wave 0 |
| SCRAPE-02 | Jobs rebuilt from DB on startup | unit | `cd backend && python -m pytest tests/services/test_scheduler.py::test_register_jobs_from_db -x` | No -- Wave 0 |
| ALERT-01 | Alert created when price <= threshold | unit | `cd backend && python -m pytest tests/services/test_alert_service.py::test_alert_fires_on_breach -x` | No -- Wave 0 |
| ALERT-01 | No alert on continued breach | unit | `cd backend && python -m pytest tests/services/test_alert_service.py::test_no_alert_continued_breach -x` | No -- Wave 0 |
| ALERT-01 | New alert on re-breach | unit | `cd backend && python -m pytest tests/services/test_alert_service.py::test_alert_fires_on_rebreach -x` | No -- Wave 0 |
| ALERT-02 | SSE stream pushes alert events | integration | `cd backend && python -m pytest tests/api/test_alerts.py::test_sse_stream -x` | No -- Wave 0 |
| ALERT-03 | Alert log endpoint returns all alerts with joined data | integration | `cd backend && python -m pytest tests/api/test_alerts.py::test_list_alerts -x` | No -- Wave 0 |
| ALERT-04 | Mark alert as read | integration | `cd backend && python -m pytest tests/api/test_alerts.py::test_mark_read -x` | No -- Wave 0 |
| ALERT-04 | Dismiss all alerts | integration | `cd backend && python -m pytest tests/api/test_alerts.py::test_dismiss_all -x` | No -- Wave 0 |
| ALERT-04 | Unread count reflects only unread | integration | `cd backend && python -m pytest tests/api/test_alerts.py::test_unread_count -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q --timeout=10`
- **Per wave merge:** `cd backend && python -m pytest tests/ -q --timeout=30`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/services/test_scheduler.py` -- covers SCRAPE-02 (scheduler registration, job add/remove, schedule mapping)
- [ ] `tests/services/test_alert_service.py` -- covers ALERT-01 (breach detection, re-breach logic, alert creation)
- [ ] `tests/api/test_alerts.py` -- covers ALERT-02, ALERT-03, ALERT-04 (SSE stream, alert CRUD endpoints)
- [ ] `tests/repositories/test_alert.py` -- covers alert repository queries (create, list, mark read, count unread)

## Sources

### Primary (HIGH confidence)
- [APScheduler 3.x User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) -- AsyncIOScheduler, IntervalTrigger, misfire_grace_time, MemoryJobStore
- [FastAPI SSE Tutorial](https://fastapi.tiangolo.com/tutorial/server-sent-events/) -- Built-in EventSourceResponse, ServerSentEvent
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) -- Version 3.11.2 confirmed as latest stable
- [FastAPI PyPI](https://pypi.org/project/fastapi/) -- Version 0.135.1 confirmed; SSE added in 0.135.0

### Secondary (MEDIUM confidence)
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) -- Version 3.3.3; confirmed as alternative but not needed
- Existing codebase: `backend/app/models/alert.py`, `backend/app/services/scrape_service.py`, `backend/main.py`, `backend/app/core/database.py`

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- APScheduler 3.x is the locked project constraint; FastAPI built-in SSE verified from official docs
- Architecture: HIGH -- Patterns derived from existing codebase conventions and official documentation
- Pitfalls: HIGH -- Based on well-documented APScheduler gotchas and async session management patterns already encountered in prior phases

**Research date:** 2026-03-18
**Valid until:** 2026-04-17 (30 days -- stable libraries)
