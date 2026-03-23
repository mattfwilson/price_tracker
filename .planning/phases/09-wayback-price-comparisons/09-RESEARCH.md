# Phase 9: Wayback Price Comparisons - Research

**Researched:** 2026-03-23
**Domain:** Backend read-only SQL queries + frontend UI enrichment (no schema migrations, no new endpoints)
**Confidence:** HIGH

## Summary

Phase 9 adds contextual price history stats to the existing watch query detail view. This is a read-only data enrichment phase -- no new database tables, no new API routes, no new pages. The work consists of: (1) adding 4-5 new repository functions for per-URL price lookups (nearest price N days ago, per-URL all-time min/max), (2) extending the `RetailerUrlWithLatest` Pydantic schema with optional wayback fields, (3) computing those fields in the existing detail endpoint handler, and (4) rendering a compact stats row in `ListingRow.tsx`.

The existing codebase already has the key building blocks: `get_rolling_avg_price(session, retailer_url_id, window_days)` returns `(avg_cents, count)` and works for both 30-day and 90-day windows. `get_all_time_min_price` exists at the query level; per-URL variants for min and max are straightforward additions. The `formatPrice()` utility and `Badge` component with green/red variants are already established patterns.

**Primary recommendation:** Structure work as backend-first (repository functions + tests), then schema/endpoint integration, then frontend display. Each layer is independently testable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 (ListingRow Layout):** Stats displayed in a compact second row below existing price/delta/badge line. Format: `30d: $51.99 (Mar 12) . 90d: $53.49 (Dec 23) . avg $50.12 (18 pts)  Good deal`. Absent fields omitted gracefully.
- **D-02 (All-Time High/Low Scope):** Per-listing (per retailer URL), not per watch query. New per-URL repo queries needed.
- **D-03 (Good Deal Indicator):** Green "Good deal" badge when current price < 90-day rolling average. Red "Above avg" badge when current price >= 90-day average. Suppressed entirely when < 3 data points in 90-day window.
- **D-04 (API Delivery):** Wayback stats embedded in `RetailerUrlWithLatest` within the existing `GET /watch-queries/{id}` response. Single round-trip.
- **D-05 (Rolling Average Suppression):** Averages suppressed when sample count < 3 for that window.

### Claude's Discretion
- Exact Tailwind classes and spacing for the compact stats row
- Whether 30d/90d ago prices use nearest-available-record or exact-day lookup (research recommends nearest-available)
- Field naming convention for wayback fields in Pydantic schema and TypeScript types
- Loading skeleton treatment for the stats row while detail data fetches

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WAYBACK-01 | Price 30d and 90d ago with actual comparison date displayed | New `get_price_near_date()` repo function; nearest-record approach with proximity window |
| WAYBACK-02 | 30-day and 90-day rolling averages with sample counts; suppressed when < 3 points | Existing `get_rolling_avg_price()` already returns (avg, count); call with window_days=30 and 90 |
| WAYBACK-03 | Good/bad deal indicator based on current price vs 90-day rolling average | Frontend Badge component with green/red variants; logic in ListingRow using avg_90d_cents |
| WAYBACK-04 | All-time high displayed alongside existing all-time low | New `get_all_time_extremes_for_url()` repo function returning (min, max) per retailer_url_id |
</phase_requirements>

## Standard Stack

### Core (already in project -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.135.0 | API framework | Already in project |
| SQLAlchemy | >=2.0.48 | Async ORM / raw SQL | Already in project |
| Pydantic | v2 (via FastAPI) | Schema validation | Already in project |
| React | 18+ | Frontend framework | Already in project |
| TanStack Query | v5 | Data fetching / caching | Already in project |
| shadcn/ui | latest | Badge, Skeleton components | Already in project |
| Tailwind CSS | v4 | Styling | Already in project |

### Supporting
No new dependencies needed. This phase is purely additive to existing code.

### Alternatives Considered
None -- all decisions are locked. The phase uses only existing stack components.

## Architecture Patterns

### Recommended Project Structure (changes only)
```
backend/app/
  repositories/
    scrape_result.py        # Add: get_price_near_date(), get_all_time_extremes_for_url()
  schemas/
    watch_query.py          # Add: optional wayback fields to RetailerUrlWithLatest
  api/
    watch_queries.py        # Modify: detail endpoint to compute and embed wayback stats

frontend/src/
  types/
    api.ts                  # Add: wayback fields to RetailerUrlWithLatest type
  components/query/
    ListingRow.tsx           # Add: WaybackStats sub-component / stats row
  lib/
    format.ts               # Add: formatShortDate() for "Mar 12" style dates
```

### Pattern 1: Nearest-Record Price Lookup (for "30d ago" / "90d ago")
**What:** Query the scrape result closest to N days ago within a proximity window, rather than requiring an exact date match.
**When to use:** When scrape frequency varies (1h to weekly) and an exact-day match would miss most lookups.
**Example:**
```python
# Source: Project codebase pattern (scrape_result.py)
async def get_price_near_date(
    session: AsyncSession,
    retailer_url_id: int,
    target_date: datetime,
    max_delta_days: int = 7,
) -> tuple[int | None, datetime | None]:
    """Return (price_cents, actual_date) for the scrape result nearest to target_date.

    Searches within +/- max_delta_days of target_date.
    Returns (None, None) if no result found within the window.
    """
    window_start = target_date - timedelta(days=max_delta_days)
    window_end = target_date + timedelta(days=max_delta_days)
    stmt = (
        select(ScrapeResult.price_cents, ScrapeResult.created_at)
        .where(
            ScrapeResult.retailer_url_id == retailer_url_id,
            ScrapeResult.created_at >= window_start,
            ScrapeResult.created_at <= window_end,
        )
        .order_by(func.abs(func.julianday(ScrapeResult.created_at) - func.julianday(target_date)))
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        return None, None
    return row[0], row[1]
```

### Pattern 2: Per-URL All-Time Extremes
**What:** Single query returning both min and max price for a retailer URL.
**Example:**
```python
async def get_all_time_extremes_for_url(
    session: AsyncSession,
    retailer_url_id: int,
) -> tuple[int | None, int | None]:
    """Return (all_time_low_cents, all_time_high_cents) for a single retailer URL."""
    stmt = select(
        func.min(ScrapeResult.price_cents),
        func.max(ScrapeResult.price_cents),
    ).where(ScrapeResult.retailer_url_id == retailer_url_id)
    result = await session.execute(stmt)
    row = result.one()
    return row[0], row[1]  # Both None if no results
```

### Pattern 3: Schema Extension with Optional Fields
**What:** Add nullable wayback fields to RetailerUrlWithLatest so the response stays backward-compatible.
**Example:**
```python
class RetailerUrlWithLatest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    created_at: datetime
    latest_result: LatestScrapeResult | None = None
    # Wayback stats (all optional -- absent when no data)
    price_30d_cents: int | None = None
    date_30d: datetime | None = None
    price_90d_cents: int | None = None
    date_90d: datetime | None = None
    avg_30d_cents: int | None = None
    avg_30d_count: int | None = None
    avg_90d_cents: int | None = None
    avg_90d_count: int | None = None
    all_time_low_cents: int | None = None
    all_time_high_cents: int | None = None
```

### Pattern 4: Frontend Stats Row (compact inline)
**What:** A sub-row within ListingRow displaying wayback stats with graceful omission.
**Example:**
```tsx
// Stats row segments -- only rendered when data exists
function WaybackStats({ url }: { url: RetailerUrlWithLatest }) {
  const segments: string[] = [];

  if (url.price_30d_cents != null && url.date_30d) {
    segments.push(`30d: ${formatPrice(url.price_30d_cents)} (${formatShortDate(url.date_30d)})`);
  }
  if (url.price_90d_cents != null && url.date_90d) {
    segments.push(`90d: ${formatPrice(url.price_90d_cents)} (${formatShortDate(url.date_90d)})`);
  }
  // Show averages only when count >= 3 (suppression rule D-05)
  if (url.avg_90d_cents != null && url.avg_90d_count != null && url.avg_90d_count >= 3) {
    segments.push(`avg ${formatPrice(url.avg_90d_cents)} (${url.avg_90d_count} pts)`);
  }

  if (segments.length === 0) return null;

  return (
    <div className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
      {segments.map((seg, i) => (
        <span key={i}>{i > 0 && <span className="mr-2">·</span>}{seg}</span>
      ))}
      <DealBadge url={url} />
    </div>
  );
}
```

### Anti-Patterns to Avoid
- **N+1 queries in the detail endpoint:** The endpoint loops over retailer URLs. Each iteration must NOT trigger individual lazy-loaded queries. Use explicit repository calls with direct SQL, not ORM relationship traversal.
- **Blocking on missing data:** If a URL has no scrape results, ALL wayback fields are None. Never error or return 500 when data is sparse.
- **Showing "N/A" labels:** Per D-03 and D-05, missing data means the element is omitted entirely, not displayed with placeholder text.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rolling averages | Custom Python iteration over results | SQLAlchemy `func.avg()` + `func.count()` (already exists as `get_rolling_avg_price`) | SQL engine handles aggregation more efficiently; edge cases (empty sets, NULLs) already tested |
| Date proximity | Python filtering of all results to find nearest | SQLite `julianday()` + `ORDER BY ABS(...)` in SQL | Avoids loading all results into memory; handles edge cases naturally |
| Price formatting | Manual string formatting | `formatPrice()` (already exists in `frontend/src/lib/format.ts`) | Consistent cents-to-dollars conversion across entire UI |
| Badge styling | Custom badge CSS | shadcn/ui `Badge` component with existing green/red Tailwind classes | Matches `[Lowest]` badge pattern exactly |

## Common Pitfalls

### Pitfall 1: SQLite julianday() with Timezone-Naive Datetimes
**What goes wrong:** The `julianday()` function works with UTC strings. If `created_at` is stored as a naive datetime and compared against a timezone-aware target, the proximity calculation gives wrong results.
**Why it happens:** The project uses `datetime.utcnow()` (naive) throughout. Consistency is key.
**How to avoid:** Use `datetime.utcnow()` for the target date calculation (matching the existing pattern in `get_rolling_avg_price`). Never pass timezone-aware datetimes to these functions.
**Warning signs:** Proximity queries returning None when data clearly exists.

### Pitfall 2: Proximity Window Too Narrow
**What goes wrong:** Using a 1-day window for "30d ago" lookup with weekly scrape schedules means most lookups return None.
**Why it happens:** Scrape frequency varies from every_1h to weekly. A 7-day default proximity window covers all schedules (2x weekly interval).
**How to avoid:** Default `max_delta_days=7` for the proximity lookup. This is documented in STATE.md as a known concern: "Wayback proximity window should be 2x scrape interval."
**Warning signs:** Stats row shows no 30d/90d prices even when price history clearly has data from that period.

### Pitfall 3: Integer Division in Average Computation
**What goes wrong:** SQLite `AVG()` returns a float, but casting to int truncates rather than rounds.
**Why it happens:** `int(row[0])` truncates. The existing `get_rolling_avg_price` already does this, so follow the same pattern for consistency (truncation, not rounding).
**How to avoid:** Use `int(row[0])` consistently (matches existing pattern). The 1-cent difference from truncation vs rounding is negligible.
**Warning signs:** Off-by-one cent in average display.

### Pitfall 4: Endpoint Performance with Many URLs
**What goes wrong:** Each retailer URL in a watch query triggers 4 new database queries (price_30d, price_90d, rolling_avg_30d, rolling_avg_90d, all_time_extremes). With 10 URLs, that's 50+ queries per detail request.
**Why it happens:** Sequential per-URL computation in a loop.
**How to avoid:** This is acceptable for a personal/local tool with SQLite (in-process, no network latency). If performance becomes an issue, batch queries using `IN` clauses. For now, keep it simple -- sequential is fine.
**Warning signs:** Detail endpoint taking > 500ms. Monitor but don't optimize prematurely.

### Pitfall 5: Frontend Suppression Logic Mismatch
**What goes wrong:** Backend sends avg with count=2, frontend shows the average anyway (or vice versa, backend suppresses but frontend tries to show).
**Why it happens:** Suppression rule (count < 3) enforced in two places.
**How to avoid:** Backend ALWAYS sends the raw avg and count values. Frontend handles suppression display logic (don't show avg when count < 3, don't show deal badge when 90d avg unavailable). Single source of truth for display rules = frontend.
**Warning signs:** Deal badge appearing when insufficient data exists.

## Code Examples

### Detail Endpoint Integration (backend)
```python
# Source: Existing pattern in backend/app/api/watch_queries.py (get_query handler)
# Add wayback computation inside the for-loop over retailer URLs:

from app.repositories.scrape_result import (
    get_price_near_date,
    get_rolling_avg_price,
    get_all_time_extremes_for_url,
)

# Inside the existing for url_obj in query.retailer_urls loop:
now = datetime.utcnow()
target_30d = now - timedelta(days=30)
target_90d = now - timedelta(days=90)

price_30d, date_30d = await get_price_near_date(db, url_obj.id, target_30d)
price_90d, date_90d = await get_price_near_date(db, url_obj.id, target_90d)
avg_30d, count_30d = await get_rolling_avg_price(db, url_obj.id, window_days=30)
avg_90d, count_90d = await get_rolling_avg_price(db, url_obj.id, window_days=90)
atl, ath = await get_all_time_extremes_for_url(db, url_obj.id)

urls_with_latest.append(
    RetailerUrlWithLatest(
        id=url_obj.id,
        url=url_obj.url,
        created_at=url_obj.created_at,
        latest_result=latest_data,
        price_30d_cents=price_30d,
        date_30d=date_30d,
        price_90d_cents=price_90d,
        date_90d=date_90d,
        avg_30d_cents=avg_30d,
        avg_30d_count=count_30d,
        avg_90d_cents=avg_90d,
        avg_90d_count=count_90d,
        all_time_low_cents=atl,
        all_time_high_cents=ath,
    )
)
```

### Short Date Formatter (frontend)
```typescript
// Add to frontend/src/lib/format.ts
export function formatShortDate(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
```

### Deal Badge Component (frontend)
```tsx
// Source: Existing Badge pattern in ListingRow.tsx
function DealBadge({ url }: { url: RetailerUrlWithLatest }) {
  // Suppress entirely when 90-day average unavailable or < 3 data points
  if (url.avg_90d_cents == null || url.avg_90d_count == null || url.avg_90d_count < 3) {
    return null;
  }

  const currentPrice = url.latest_result?.price_cents;
  if (currentPrice == null) return null;

  const isGoodDeal = currentPrice < url.avg_90d_cents;

  return isGoodDeal ? (
    <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
      Good deal
    </Badge>
  ) : (
    <Badge className="bg-red-500/15 text-red-400 border-red-500/30">
      Above avg
    </Badge>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Query-level all-time low only | Per-URL all-time low + high | Phase 9 (new) | Existing `get_all_time_min_price` stays for QueryCard badge; new per-URL variant added |
| No historical price context | 30d/90d wayback + rolling averages | Phase 9 (new) | `get_rolling_avg_price` already exists and works; just needs to be called with window_days=90 too |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio |
| Config file | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && python -m pytest tests/repositories/test_scrape_result.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WAYBACK-01 | `get_price_near_date` returns nearest price within proximity window; returns None outside window | unit | `cd backend && python -m pytest tests/repositories/test_scrape_result.py::TestPriceNearDate -x` | No -- Wave 0 |
| WAYBACK-02 | `get_rolling_avg_price` with window_days=90; suppression when count < 3 | unit | `cd backend && python -m pytest tests/repositories/test_scrape_result.py::TestRollingAvg -x` | Partial -- 30-day tests exist, need 90-day variant |
| WAYBACK-03 | Deal indicator logic (good deal when price < avg, above avg otherwise, suppressed when < 3 pts) | unit | Frontend logic only -- tested via WAYBACK-01/02 backend + manual UI check | Manual-only (UI display logic) |
| WAYBACK-04 | `get_all_time_extremes_for_url` returns per-URL min and max | unit | `cd backend && python -m pytest tests/repositories/test_scrape_result.py::TestAllTimeExtremes -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/repositories/test_scrape_result.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/repositories/test_scrape_result.py::TestPriceNearDate` -- covers WAYBACK-01 (nearest record lookup, edge cases: no data, outside window, exact match)
- [ ] `tests/repositories/test_scrape_result.py::TestAllTimeExtremes` -- covers WAYBACK-04 (per-URL min/max, no results returns None)
- [ ] `tests/repositories/test_scrape_result.py::TestRollingAvg` -- extend for 90-day window_days parameter (WAYBACK-02)

## Open Questions

1. **Proximity window default value**
   - What we know: STATE.md says "2x scrape interval." Scrape schedules range from every_1h to weekly.
   - What's unclear: Whether 7 days is sufficient for all cases (weekly schedule + a missed scrape = 14 days gap).
   - Recommendation: Use `max_delta_days=7` as default. For weekly schedules, 7 days covers one interval. If a weekly scrape is missed entirely, showing no 30d price is the correct behavior (no data in range).

2. **SQLite julianday() availability**
   - What we know: `julianday()` is a built-in SQLite function, always available.
   - What's unclear: Whether SQLAlchemy exposes it directly or needs `func.julianday()`.
   - Recommendation: Use `func.julianday()` -- SQLAlchemy passes unrecognized function names through to the database. HIGH confidence this works with SQLite.

## Sources

### Primary (HIGH confidence)
- `backend/app/repositories/scrape_result.py` -- existing `get_rolling_avg_price()` and `get_all_time_min_price()` implementations
- `backend/app/schemas/watch_query.py` -- current `RetailerUrlWithLatest` schema (line 102-108)
- `backend/app/api/watch_queries.py` -- detail endpoint handler (lines 57-133)
- `frontend/src/components/query/ListingRow.tsx` -- current layout and Badge pattern
- `frontend/src/types/api.ts` -- current TypeScript types
- `frontend/src/lib/format.ts` -- existing `formatPrice()` and date formatters

### Secondary (MEDIUM confidence)
- SQLite documentation: `julianday()` is a core date/time function, available in all SQLite versions 3.x+

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing libraries
- Architecture: HIGH -- patterns directly derived from existing codebase (get_rolling_avg_price, ListingRow)
- Pitfalls: HIGH -- identified from actual code review (proximity windows, suppression logic, query count)

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (stable -- no external dependencies changing)
