# Phase 8: Scrape Health Dashboard - Research

**Researched:** 2026-03-23
**Domain:** Per-URL scrape attempt tracking, health status computation, dashboard UI
**Confidence:** HIGH

## Summary

Phase 8 adds per-URL scrape attempt tracking via a new `scrape_url_attempts` table, a computed health status layer (healthy/degraded/failing), a dedicated `/health` page with sortable/filterable table, and per-URL mini-dots on QueryCards. The phase spans backend (data model, migration, service integration, API endpoint) and frontend (new page, new components, modified existing components).

The existing codebase provides clear patterns for every layer: Alembic migrations with `batch_alter_table` for SQLite, SQLAlchemy async models, Pydantic response schemas, FastAPI routers, TanStack Query hooks, and shadcn/Tailwind UI components. No new dependencies are needed. The primary complexity is in correctly wiring attempt tracking into the scrape service's per-URL loop (both success and failure paths) and computing health stats efficiently via SQL.

**Primary recommendation:** Implement in three waves: (1) backend data model + migration + service integration, (2) backend API endpoint + health computation logic, (3) frontend health page + QueryCard integration.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Add a new `scrape_url_attempts` table -- one row per URL per scrape attempt: `retailer_url_id`, `scraped_at`, `is_success` (bool), `error_type` (string), `error_message` (text, nullable). Requires Alembic migration.
- **D-02:** Error type stored as a freeform string (exception class name or scraper failure label) -- not an enum. Flexible when new error types emerge. Claude picks the appropriate convention based on existing `BaseExtractor` failure patterns.
- **D-03:** Scrape service must write a row to `scrape_url_attempts` for every URL on every attempt (both success and failure).
- **D-04:** Window = **last 10 attempts** per URL (not calendar-based).
- **D-05:** Status categories: Healthy (green) >= 80% (8+ of 10), Degraded (yellow) 50-79%, Failing (red) < 50%.
- **D-06:** URLs with fewer than 10 attempts use actual count as denominator (no padding).
- **D-07:** New route `/health` with nav item in header alongside Alerts.
- **D-08:** Table layout -- one row per retailer URL. Columns: status dot, URL (domain), watch query name, success rate, last successful scrape timestamp, consecutive failure count, last error type.
- **D-09:** Sortable by: status (failing first), watch query name, last success date.
- **D-10:** Filterable to show only degraded or failing URLs.
- **D-11:** Read-only -- no inline actions.
- **D-12:** Per-URL mini-dots appear below StatusDot on QueryCard.
- **D-13:** Each dot shows the URL's domain label.
- **D-14:** Tooltip: `{domain} . {success_count}/{window} . last success {relative_time}`. Use title attribute.
- **D-15:** Existing StatusDot preserved -- mini-dots are additional.

### Claude's Discretion
- Error type string convention (e.g., "blocked", "network_error", "parse_error") -- base on existing `BaseExtractor` / `FailureType` patterns
- Exact Tailwind classes, spacing, and icon choices for the health page table
- Whether to use a separate API endpoint (`GET /health/urls`) or extend existing watch-queries response
- Loading skeleton strategy for health page data

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HEALTH-01 | User can view a health dashboard page listing all retailer URLs with per-URL success rate (last N attempts), last successful scrape timestamp, consecutive failure count, and last error type | New `scrape_url_attempts` table + health API endpoint + HealthPage frontend |
| HEALTH-02 | Retailer URLs are visually categorized as healthy (green), degraded (yellow), or failing (red) based on recent scrape outcomes | Threshold computation from D-04/D-05/D-06 applied server-side, rendered with HealthStatusDot component |
| HEALTH-03 | User can sort and filter the health URL list by status, watch query, and last success date | Client-side sort/filter on HealthTable, HealthFilter component |
| HEALTH-04 | Dashboard query cards show a health status indicator for each URL at a glance | UrlHealthDots component on QueryCard, health data embedded in watch-query detail response or fetched separately |

</phase_requirements>

## Standard Stack

### Core (already in project -- no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | >=2.0.48 | Async ORM for `scrape_url_attempts` model | Already used for all models |
| Alembic | >=1.18.0 | Database migration for new table | Already used, auto-runs on startup |
| FastAPI | >=0.135.0 | New health API router | Existing pattern |
| Pydantic | v2 (via FastAPI) | Health response schemas | Existing pattern |
| React | 18.x | Frontend components | Existing |
| TanStack Query | v5 | `useHealthData()` hook | Existing pattern from `use-watch-queries.ts` |
| shadcn/ui | latest | Table, Button, Skeleton, Tooltip components | Already initialized in project |
| Tailwind CSS | v4 | Styling | Existing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | (installed) | ArrowUp/ArrowDown sort icons | Health table column headers |
| react-router-dom | (installed) | NavLink for Health nav item | Header navigation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate `/health/urls` endpoint | Extend watch-queries detail response | Separate endpoint is cleaner -- health page needs cross-query data, while detail is per-query. Recommend **separate endpoint**. |
| Server-side sort/filter | Client-side sort/filter | With <100 URLs typical for personal use, client-side is simpler and avoids API complexity. Recommend **client-side**. |

**Installation:** No new packages needed.

## Architecture Patterns

### Recommended Project Structure (new files)
```
backend/
├── app/
│   ├── models/
│   │   └── scrape_url_attempt.py     # New model
│   ├── repositories/
│   │   └── scrape_url_attempt.py     # New CRUD + health queries
│   ├── schemas/
│   │   └── health.py                 # New Pydantic schemas
│   └── api/
│       └── health.py                 # New router
├── alembic/versions/
│   └── xxxx_add_scrape_url_attempts.py  # New migration
└── tests/
    ├── repositories/
    │   └── test_scrape_url_attempt.py   # New tests
    └── api/
        └── test_health.py               # New tests

frontend/src/
├── pages/
│   └── HealthPage.tsx                # New page
├── components/health/
│   ├── HealthTable.tsx               # New component
│   ├── HealthStatusDot.tsx           # New component
│   └── HealthFilter.tsx              # New component
├── components/dashboard/
│   └── UrlHealthDots.tsx             # New component
├── hooks/
│   └── use-health.ts                 # New hook (or extend use-watch-queries.ts)
└── types/
    └── api.ts                        # Add health types
```

### Pattern 1: Attempt Recording in Scrape Loop

**What:** Write a `scrape_url_attempts` row for every URL on every scrape attempt in `run_scrape_job()`.
**When to use:** Inside the per-URL for-loop in `scrape_service.py` (lines 117-133).
**Critical detail:** The attempt row must be written AFTER the scrape completes (success or failure), within the same DB session. On success, `is_success=True`, `error_type=None`. On failure, `is_success=False`, `error_type` from `ScrapeError.failure_type.value` or exception class name.

```python
# In run_scrape_job(), inside the for-loop:
for retailer_url in urls:
    try:
        data = await scrape_single_url(browser_manager, retailer_url.url)
        await create_scrape_result(session, ...)
        # Record success attempt
        await create_scrape_url_attempt(
            session, retailer_url_id=retailer_url.id,
            is_success=True, error_type=None, error_message=None,
        )
        successes += 1
    except ScrapeError as e:
        # Record failure attempt with typed error
        await create_scrape_url_attempt(
            session, retailer_url_id=retailer_url.id,
            is_success=False,
            error_type=e.failure_type.value,  # "NETWORK_ERROR", "EXTRACTION_ERROR", "BLOCKED"
            error_message=e.message,
        )
        failures += 1
        error_messages.append(f"{retailer_url.url}: {e}\n")
    except Exception as e:
        # Record failure with generic error type
        await create_scrape_url_attempt(
            session, retailer_url_id=retailer_url.id,
            is_success=False,
            error_type=type(e).__name__,
            error_message=str(e),
        )
        failures += 1
        error_messages.append(f"{retailer_url.url}: {e}\n")
```

### Pattern 2: Health Stats Computation via SQL

**What:** Compute success rate, consecutive failures, and last success in a single efficient query per URL.
**When to use:** In the health API endpoint's repository layer.

```python
# Window query: last 10 attempts per URL using row_number()
from sqlalchemy import case, func, literal_column, select
from sqlalchemy.orm import aliased

# Subquery: last N attempts per retailer_url_id
window_sub = (
    select(
        ScrapeUrlAttempt.retailer_url_id,
        ScrapeUrlAttempt.is_success,
        ScrapeUrlAttempt.error_type,
        ScrapeUrlAttempt.scraped_at,
        func.row_number().over(
            partition_by=ScrapeUrlAttempt.retailer_url_id,
            order_by=ScrapeUrlAttempt.scraped_at.desc(),
        ).label("rn"),
    )
).subquery()

# Aggregate within window
stats = (
    select(
        window_sub.c.retailer_url_id,
        func.count().label("window_size"),
        func.sum(case((window_sub.c.is_success == True, 1), else_=0)).label("success_count"),
    )
    .where(window_sub.c.rn <= 10)
    .group_by(window_sub.c.retailer_url_id)
)
```

### Pattern 3: Error Type Convention

**What:** Use `FailureType` enum `.value` strings for error_type in attempts.
**Existing values from `base.py`:**
- `"NETWORK_ERROR"` -- timeouts, connection failures
- `"EXTRACTION_ERROR"` -- page loaded but data extraction failed
- `"BLOCKED"` -- HTTP 403/429/503 responses

For non-ScrapeError exceptions, use the Python exception class name (e.g., `"TimeoutError"`, `"RuntimeError"`).

### Pattern 4: API Endpoint Design

**What:** Separate `GET /health/urls` endpoint returning all URLs with health stats.
**Why separate:** The health page needs a cross-query view of ALL URLs. The existing watch-queries detail endpoint is per-query. A separate endpoint avoids N+1 queries and keeps concerns separated.

**Important conflict:** `backend/main.py` already has `@app.get("/health")` returning `{"status": "ok"}` for server health checks. The new health router MUST use a different prefix, such as `/scrape-health` or the router can be mounted at `/health` with the URL health list at `/health/urls`, while the existing server health check stays at `/health` (on the app directly, not via router). Since the existing `/health` is registered directly on the FastAPI app instance (not via a router), and routers with prefixes take specific paths, the cleanest approach is:
- Keep existing `@app.get("/health")` as-is for server health
- New router: `APIRouter(prefix="/scrape-health", tags=["scrape-health"])`
- Endpoint: `GET /scrape-health/urls`

### Anti-Patterns to Avoid
- **Computing health stats in Python loops:** Use SQL aggregation, not fetching all attempts and computing in Python. SQLite handles `row_number()` window functions fine (added in 3.25.0, all modern SQLite versions).
- **Storing computed health status:** Don't add a `status` column to `retailer_urls`. Compute from attempts on read. Avoids stale data.
- **Blocking the scrape loop:** Attempt recording is a simple INSERT -- no risk of blocking, but ensure it happens inside the existing session transaction.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table UI | Custom table HTML | shadcn `Table` component | Already available, handles styling, accessible |
| Sort state management | Custom sort reducer | Simple `useState` with comparator | <100 rows, no performance concern |
| Domain extraction from URL | Regex parser | `new URL(url).hostname` | Standard browser API, handles all edge cases |
| Relative time formatting | Custom date math | Existing `formatRelativeTime()` from `lib/format.ts` | Already used by QueryCard |
| Loading skeletons | Custom shimmer | shadcn `Skeleton` component | Established pattern from AlertsPage |

**Key insight:** Every UI pattern needed already exists in the project. The health page is essentially a variant of the AlertsPage (table + filter) with different data.

## Common Pitfalls

### Pitfall 1: Missing Attempt on Exception Path
**What goes wrong:** Attempt row not written when an unexpected exception (not ScrapeError) occurs in the scrape loop.
**Why it happens:** The current code has `except (ScrapeError, Exception) as e` which catches everything, but the new attempt recording must handle both ScrapeError (has `failure_type`) and generic Exception (no `failure_type`) differently.
**How to avoid:** Split into two except clauses: `except ScrapeError` and `except Exception`. Each writes an attempt row with appropriate error_type.
**Warning signs:** Success rate showing 100% even when scrape_jobs show failures.

### Pitfall 2: API Path Collision with Existing /health
**What goes wrong:** New health router shadows the existing `@app.get("/health")` server health check endpoint.
**Why it happens:** `backend/main.py` line 59 already defines `GET /health` returning `{"status": "ok"}`.
**How to avoid:** Use prefix `/scrape-health` for the new router, not `/health`.
**Warning signs:** Server health check returns HTML or 404 after deploying.

### Pitfall 3: N+1 Queries for QueryCard Health Dots
**What goes wrong:** Each QueryCard fires a separate API call to get health data for its URLs, causing N+1 requests.
**Why it happens:** Following the existing pattern where each QueryCard fetches its own detail.
**How to avoid:** Either (a) embed minimal health data in the watch-query detail response (adds `url_health` array to `WatchQueryDetailResponse`), or (b) fetch all health data once and distribute via React context. Option (a) is simpler and consistent with how `latest_result` is already embedded.
**Warning signs:** Network waterfall of health requests on dashboard load.

### Pitfall 4: SQLite Window Function Compatibility
**What goes wrong:** Assuming `row_number()` isn't available in SQLite.
**Why it happens:** Old SQLite versions (<3.25.0) don't support window functions.
**How to avoid:** Modern Python ships with SQLite >=3.25. Verify with `sqlite3.sqlite_version`. Alternatively, use a simpler approach: `ORDER BY scraped_at DESC LIMIT 10` per URL in a subquery.
**Warning signs:** SQL errors about "window functions" on startup.

### Pitfall 5: Consecutive Failure Count Computation
**What goes wrong:** Computing consecutive failures incorrectly by counting all failures in the window instead of only trailing consecutive failures.
**Why it happens:** Confusing "total failures in last 10" with "failures since last success."
**How to avoid:** Consecutive failures = count of attempts before the first success when ordered newest-to-oldest. If all 10 are failures, consecutive = 10. If latest is success, consecutive = 0.
**Warning signs:** Consecutive failure count equals total failure count even when there are intervening successes.

### Pitfall 6: Backfill Decision
**What goes wrong:** Existing URLs show "no data" on the health page immediately after migration because there are no attempt records for past scrapes.
**Why it happens:** The `scrape_url_attempts` table starts empty; historical scrapes only exist in `scrape_results` (successes) and `scrape_jobs` (job-level errors).
**How to avoid:** Per STATE.md blocker note, the decision is to **start fresh from migration date** -- no backfill. Document this in the migration. URLs will show health data only after they've been scraped post-migration.
**Warning signs:** Users confused about "no data" for URLs that have been scraping for weeks.

## Code Examples

### New Model: ScrapeUrlAttempt

```python
# backend/app/models/scrape_url_attempt.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class ScrapeUrlAttempt(Base):
    """One row per URL per scrape attempt (both success and failure)."""
    __tablename__ = "scrape_url_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_url_id: Mapped[int] = mapped_column(ForeignKey("retailer_urls.id"))
    scraped_at: Mapped[datetime] = mapped_column(server_default=func.now())
    is_success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    retailer_url: Mapped["RetailerUrl"] = relationship()
```

### Alembic Migration Pattern

```python
# Following existing pattern from a3b7c9d1e4f2
def upgrade() -> None:
    op.create_table(
        'scrape_url_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('retailer_url_id', sa.Integer(), sa.ForeignKey('retailer_urls.id'), nullable=False),
        sa.Column('scraped_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('is_success', sa.Boolean(), default=False, nullable=False),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    op.create_index('ix_scrape_url_attempts_retailer_url_id', 'scrape_url_attempts', ['retailer_url_id'])
    op.create_index('ix_scrape_url_attempts_scraped_at', 'scrape_url_attempts', ['scraped_at'])

def downgrade() -> None:
    op.drop_table('scrape_url_attempts')
```

### Health API Response Schema

```python
# backend/app/schemas/health.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class UrlHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    retailer_url_id: int
    url: str
    domain: str  # extracted from URL
    watch_query_id: int
    watch_query_name: str
    status: str  # "healthy" | "degraded" | "failing"
    success_count: int
    window_size: int  # actual attempts (may be < 10 for new URLs)
    last_success_at: datetime | None
    consecutive_failures: int
    last_error_type: str | None

class HealthListResponse(BaseModel):
    urls: list[UrlHealthResponse]
```

### Frontend Hook Pattern

```typescript
// Following existing use-watch-queries.ts pattern
export const healthKeys = {
  urls: ["health", "urls"] as const,
};

export function useHealthUrls() {
  return useQuery({
    queryKey: healthKeys.urls,
    queryFn: () => apiFetch<UrlHealthResponse[]>("/scrape-health/urls"),
  });
}
```

### HealthStatusDot Component

```tsx
// Reuses StatusDot color palette but smaller (h-2 w-2)
type HealthStatus = "healthy" | "degraded" | "failing";

const healthConfig: Record<HealthStatus, { color: string; label: string }> = {
  healthy: { color: "bg-emerald-500", label: "Healthy" },
  degraded: { color: "bg-amber-500", label: "Degraded" },
  failing: { color: "bg-red-500", label: "Failing" },
};
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Job-level error tracking only (`scrape_jobs.error_message`) | Per-URL attempt tracking (`scrape_url_attempts`) | This phase | Enables per-URL health visibility |
| No failure visibility on dashboard | Per-URL mini-dots on QueryCard | This phase | At-a-glance health without navigation |

**Note on backfill:** STATE.md flags this as a blocker to resolve during planning. Recommendation: **start fresh** -- no backfill. The `scrape_url_attempts` table populates naturally after migration. Backfilling from `scrape_results` (successes only) would create artificially high success rates and miss all failures. Backfilling from `scrape_jobs` is unreliable since errors are concatenated per-job, not per-URL.

## Open Questions

1. **QueryCard health data delivery**
   - What we know: QueryCard already fetches per-query detail. Health data could be embedded in WatchQueryDetailResponse or fetched separately.
   - What's unclear: Performance tradeoff of embedding vs separate fetch.
   - Recommendation: **Embed in WatchQueryDetailResponse.** Add a `url_health` array to the detail response. This avoids extra API calls and follows the existing pattern of embedding `latest_result` per URL. The health data is lightweight (a few fields per URL) and the detail endpoint already loads retailer_urls.

2. **Index strategy for scrape_url_attempts**
   - What we know: Queries will filter by `retailer_url_id` and order by `scraped_at DESC`.
   - What's unclear: Whether a composite index is better than separate indexes.
   - Recommendation: Create a composite index on `(retailer_url_id, scraped_at DESC)` for optimal query performance on the windowed lookups. Also create a single-column index on `retailer_url_id` for FK lookups.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | pytest 8.x + pytest-asyncio (asyncio_mode=auto) |
| Framework (frontend) | vitest + @testing-library/react (jsdom) |
| Config file (backend) | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Config file (frontend) | `frontend/vitest.config.ts` |
| Quick run command (backend) | `cd backend && python -m pytest tests/ -x -q` |
| Quick run command (frontend) | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q && cd ../frontend && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HEALTH-01 | Attempt rows created on scrape; health stats computed correctly | unit | `cd backend && python -m pytest tests/repositories/test_scrape_url_attempt.py -x` | Wave 0 |
| HEALTH-01 | Health API returns correct URL list with stats | integration | `cd backend && python -m pytest tests/api/test_health.py -x` | Wave 0 |
| HEALTH-02 | Status thresholds (healthy/degraded/failing) applied correctly | unit | `cd backend && python -m pytest tests/repositories/test_scrape_url_attempt.py::test_health_status_thresholds -x` | Wave 0 |
| HEALTH-03 | Client-side sort and filter | unit | `cd frontend && npx vitest run src/__tests__/HealthTable.test.tsx` | Wave 0 |
| HEALTH-04 | QueryCard renders health mini-dots | unit | `cd frontend && npx vitest run src/__tests__/UrlHealthDots.test.tsx` | Wave 0 |
| HEALTH-01 | Scrape service writes attempt on success and failure | unit | `cd backend && python -m pytest tests/scrapers/test_scrape_service.py -x` | Exists (modify) |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q` (backend) or `cd frontend && npx vitest run` (frontend)
- **Per wave merge:** Full suite: both backend and frontend tests
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/repositories/test_scrape_url_attempt.py` -- covers HEALTH-01, HEALTH-02 (attempt CRUD + health stat computation + threshold logic)
- [ ] `backend/tests/api/test_health.py` -- covers HEALTH-01 (API endpoint returns correct response shape)
- [ ] `frontend/src/__tests__/HealthTable.test.tsx` -- covers HEALTH-03 (sort, filter behavior)
- [ ] `frontend/src/__tests__/UrlHealthDots.test.tsx` -- covers HEALTH-04 (mini-dot rendering, tooltip content)
- [ ] Modify `backend/tests/scrapers/test_scrape_service.py` -- covers HEALTH-01 (attempt recording in scrape loop)

## Sources

### Primary (HIGH confidence)
- Project source code: `backend/app/scrapers/base.py` -- FailureType enum values verified
- Project source code: `backend/app/services/scrape_service.py` -- scrape loop structure verified
- Project source code: `backend/main.py` -- existing `/health` endpoint collision identified
- Project source code: All existing model, schema, API, and frontend patterns verified by reading actual files
- CONTEXT.md -- all locked decisions verified against codebase feasibility

### Secondary (MEDIUM confidence)
- SQLite window function support (row_number) -- available since SQLite 3.25.0 (2018-09-15). Python 3.10+ ships with SQLite >=3.37.

### Tertiary (LOW confidence)
- None -- all findings verified against project source code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns established in codebase
- Architecture: HIGH -- direct extension of existing patterns, all integration points verified
- Pitfalls: HIGH -- identified from reading actual source code, especially the `/health` endpoint collision

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- no external dependency changes)
