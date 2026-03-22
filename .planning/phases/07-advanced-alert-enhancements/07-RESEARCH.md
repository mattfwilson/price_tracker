# Phase 7: Advanced Alert Enhancements - Research

**Researched:** 2026-03-22
**Domain:** Alert evaluation logic, SQL aggregation, Alembic migrations, React form/badge UI
**Confidence:** HIGH

## Summary

Phase 7 adds three alert enhancements to the existing price tracker: percentage-based price drop alerts (ALERT-05), all-time low badge display (ALERT-06), and alert cooldown to prevent spam (ALERT-07). The existing codebase has a clean separation between alert evaluation (`alert_service.py`), alert persistence (`repositories/alert.py`), and the scrape orchestration that triggers evaluation (`scheduler.py` and `scrapes.py`). All three requirements build on this existing architecture with well-defined extension points.

The implementation requires: (1) an Alembic migration adding three nullable columns to `watch_queries`, (2) new SQL queries in repositories for rolling average and all-time minimum, (3) modifications to `evaluate_alerts_for_job` to check percentage drop and cooldown conditions, (4) a new `is_all_time_low` field on the `WatchQueryDetailResponse`, and (5) frontend form fields and badge display in `QueryCard`.

**Primary recommendation:** Extend the existing `alert_service.evaluate_alerts_for_job` with two additional guard checks (cooldown first, then percentage-based alert), add the all-time low computation to the GET detail endpoint, and surface both new fields and the all-time-low badge through the existing schema/component chain.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ALERT-05 | Percentage-based price drop alert when price is X% below 30-day rolling average | Rolling average SQL query pattern, minimum sample threshold, `evaluate_alerts_for_job` extension point, new `pct_drop_threshold` column on `watch_queries` |
| ALERT-06 | All-time low badge on QueryCard when current lowest price is the lowest ever recorded | All-time minimum SQL query via `func.min()`, `is_all_time_low` boolean on detail response, Badge component already in use on QueryCard |
| ALERT-07 | Alert cooldown prevents duplicate alerts within configurable time window | Cooldown check via `MAX(alerts.created_at)` query, `alert_cooldown_hours` column on `watch_queries`, guard at top of evaluation loop |
</phase_requirements>

## Standard Stack

No new libraries are needed. All features are implemented with the existing stack.

### Core (already installed)
| Library | Purpose | Why Standard |
|---------|---------|--------------|
| SQLAlchemy 2.x async | ORM + raw SQL aggregations (func.avg, func.min, func.max) | Already the project ORM |
| Alembic | Schema migration for new columns | Already configured with single migration file |
| Pydantic v2 | Schema validation for new optional fields | Already used for all API schemas |
| React + TypeScript | Frontend form fields and badge rendering | Already the frontend stack |
| shadcn/ui Badge | "All-Time Low" badge display | Already imported and used in QueryCard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQL AVG() for rolling average | Python-side calculation | SQL is faster and handles NULLs; Python would require loading all rows into memory |
| Column-level cooldown_hours | Separate cooldown_config table | Over-engineering for single-user app; a column on watch_queries is sufficient |

## Architecture Patterns

### Current Alert Evaluation Flow
```
scheduler.scheduled_scrape()
  -> scrape_service.run_scrape_job()
  -> alert_service.evaluate_alerts_for_job()
      -> for each scrape_result:
           should_fire_alert() -> checks threshold + re-breach
           create_alert() -> persists + broadcasts SSE
```

The same flow is triggered by `scrapes.py::trigger_scrape` for on-demand scrapes.

### Extended Alert Evaluation Flow (Phase 7)
```
evaluate_alerts_for_job()
  -> for each scrape_result:
       1. check_cooldown() -> if within cooldown window, skip entirely (ALERT-07)
       2. should_fire_alert() -> existing threshold + re-breach check (ALERT-01)
       3. should_fire_pct_drop_alert() -> new % drop check (ALERT-05)
       4. if either (2) or (3) fires -> create_alert() with alert_type tag
```

### Pattern 1: Alembic Migration for Nullable Columns
**What:** Add three nullable columns to `watch_queries` table via Alembic migration
**When to use:** When extending an existing table with optional new fields
**Example:**
```python
# alembic/versions/xxxx_add_alert_enhancement_columns.py
def upgrade() -> None:
    op.add_column('watch_queries', sa.Column('pct_drop_threshold', sa.Float(), nullable=True))
    op.add_column('watch_queries', sa.Column('alert_cooldown_hours', sa.Integer(), server_default='24', nullable=False))

def downgrade() -> None:
    op.drop_column('watch_queries', 'alert_cooldown_hours')
    op.drop_column('watch_queries', 'pct_drop_threshold')
```

### Pattern 2: SQL Aggregation for Rolling Average
**What:** Compute 30-day rolling average price from scrape_results using SQL `func.avg()`
**When to use:** When computing aggregates over time-windowed data
**Example:**
```python
from sqlalchemy import func, select
from datetime import datetime, timedelta

async def get_rolling_avg_price(
    session: AsyncSession,
    retailer_url_id: int,
    window_days: int = 30,
) -> tuple[int | None, int]:
    """Return (average_price_cents, sample_count) for the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=window_days)
    stmt = (
        select(
            func.avg(ScrapeResult.price_cents),
            func.count(ScrapeResult.id),
        )
        .where(ScrapeResult.retailer_url_id == retailer_url_id)
        .where(ScrapeResult.created_at >= cutoff)
    )
    result = await session.execute(stmt)
    row = result.one()
    avg_price = int(row[0]) if row[0] is not None else None
    count = row[1]
    return avg_price, count
```

### Pattern 3: All-Time Minimum Query
**What:** Check if current price is the minimum ever recorded across all retailer URLs for a watch query
**When to use:** For ALERT-06 all-time low badge
**Example:**
```python
async def get_all_time_min_price(
    session: AsyncSession,
    watch_query_id: int,
) -> int | None:
    """Return the minimum price_cents ever recorded for any retailer URL of this watch query."""
    stmt = (
        select(func.min(ScrapeResult.price_cents))
        .join(RetailerUrl, ScrapeResult.retailer_url_id == RetailerUrl.id)
        .where(RetailerUrl.watch_query_id == watch_query_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

### Pattern 4: Alert Cooldown Check
**What:** Query the most recent alert timestamp for a watch query and compare against cooldown window
**When to use:** Before creating any alert, to suppress duplicates within cooldown period
**Example:**
```python
async def is_within_cooldown(
    session: AsyncSession,
    watch_query_id: int,
    cooldown_hours: int,
) -> bool:
    """Return True if an alert was created within the cooldown window."""
    stmt = (
        select(func.max(Alert.created_at))
        .where(Alert.watch_query_id == watch_query_id)
    )
    result = await session.execute(stmt)
    last_alert_at = result.scalar_one_or_none()
    if last_alert_at is None:
        return False
    cutoff = datetime.utcnow() - timedelta(hours=cooldown_hours)
    return last_alert_at >= cutoff
```

### Anti-Patterns to Avoid
- **Loading all scrape_results into Python for averaging:** Use SQL `func.avg()` to let SQLite do the work. The scrape_results table will grow over time; aggregating in Python wastes memory.
- **Checking cooldown per-listing instead of per-query:** The requirement says cooldown is per watch query. A single cooldown check before the per-result loop is cleaner and more correct.
- **Making pct_drop_threshold required:** It must be nullable -- users who only want absolute threshold alerts should not be forced to set a percentage.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-windowed average | Python loop over all results | `func.avg()` with `WHERE created_at >= cutoff` | SQLite handles this efficiently; avoids loading entire history |
| All-time minimum | Python min() over fetched rows | `func.min()` with JOIN | Single SQL query, O(1) memory |
| Timezone math for cooldown | Manual datetime arithmetic | `datetime.utcnow() - timedelta(hours=N)` | Project already uses UTC throughout (server_default=func.now()) |

## Common Pitfalls

### Pitfall 1: Cooldown Bypassed on First Alert
**What goes wrong:** If `is_within_cooldown` is checked before `should_fire_alert`, and there's never been an alert (cooldown returns False), but then two results in the same job both trigger alerts -- the second alert fires within the same evaluation loop before the first alert's timestamp is visible.
**Why it happens:** The cooldown check queries `MAX(alerts.created_at)`, but the first alert from the same job was just flushed (not committed) so its timestamp IS visible within the same session.
**How to avoid:** This is actually fine -- the flush in `create_alert` makes the first alert visible to subsequent queries within the same session. The cooldown check naturally applies after the first alert fires. No special handling needed.
**Warning signs:** Multiple alerts for the same query in the same scrape job when cooldown is set.

### Pitfall 2: Rolling Average with Insufficient Data
**What goes wrong:** A watch query is brand new with only 1-2 scrape results. The "30-day average" is essentially the current price, making any percentage drop calculation meaningless.
**Why it happens:** `func.avg()` over 1 row returns that row's value; a 10% drop would require the price to be 10% below itself, which never fires.
**How to avoid:** Set a minimum sample count (e.g., 3 results) before the percentage drop alert is evaluated. If fewer samples exist, skip the percentage check silently.
**Warning signs:** Users wonder why their percentage alert "never fires" on new queries.

### Pitfall 3: Float Precision in Percentage Comparison
**What goes wrong:** Comparing `current_price < avg_price * (1 - pct_threshold/100)` with floats can produce off-by-one-cent errors.
**Why it happens:** Floating point arithmetic on cents.
**How to avoid:** All prices are stored as integer cents. Compute the target as `int(avg_price * (1 - pct_threshold / 100))` and compare integers. The pct_drop_threshold itself is a float (e.g., 10.0 for 10%), but the comparison target should be truncated to int cents.
**Warning signs:** Alert fires at 9.99% instead of 10%.

### Pitfall 4: Migration Needs Server Default for Non-Nullable Column
**What goes wrong:** Adding `alert_cooldown_hours` as non-nullable to an existing table with rows fails if no default is provided.
**Why it happens:** SQLite requires either nullable=True or a server_default for ADD COLUMN on tables with existing data.
**How to avoid:** Use `server_default='24'` in the migration for `alert_cooldown_hours`. For `pct_drop_threshold`, make it nullable (null = feature disabled).
**Warning signs:** `alembic upgrade head` fails with "Cannot add a NOT NULL column with default value NULL".

### Pitfall 5: Cooldown Applies to Both Alert Types
**What goes wrong:** A percentage-drop alert fires, starting the cooldown. Then a threshold alert (ALERT-01) is suppressed by the same cooldown even though they're different alert types.
**Why it happens:** Single cooldown window per watch query covers all alert types.
**How to avoid:** This is actually the desired behavior per the requirement ("alert cooldown prevents duplicate alerts from firing within a configurable time window"). The cooldown applies to the watch query as a whole, not per alert type. Document this in the UI help text.
**Warning signs:** Users expect separate cooldowns for threshold vs. percentage alerts.

## Code Examples

### WatchQuery Model Extension
```python
# backend/app/models/watch_query.py - add to existing class
from sqlalchemy import Float

class WatchQuery(Base, TimestampMixin):
    # ... existing fields ...

    # Phase 7: Percentage drop alert threshold (e.g., 10.0 = 10%)
    # NULL means disabled
    pct_drop_threshold: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    # Phase 7: Alert cooldown in hours (default 24)
    alert_cooldown_hours: Mapped[int] = mapped_column(Integer, default=24)
```

### WatchQueryCreate Schema Extension
```python
# backend/app/schemas/watch_query.py - add to existing schemas
class WatchQueryCreate(BaseModel):
    # ... existing fields ...
    pct_drop_threshold: float | None = None  # e.g., 10.0 for 10%
    alert_cooldown_hours: int = 24

    @field_validator("pct_drop_threshold")
    @classmethod
    def pct_threshold_range(cls, v: float | None) -> float | None:
        if v is not None and (v <= 0 or v > 100):
            raise ValueError("pct_drop_threshold must be between 0 and 100")
        return v

    @field_validator("alert_cooldown_hours")
    @classmethod
    def cooldown_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("alert_cooldown_hours must be non-negative")
        return v
```

### WatchQueryResponse Schema Extension
```python
class WatchQueryResponse(BaseModel):
    # ... existing fields ...
    pct_drop_threshold: float | None = None
    alert_cooldown_hours: int

class WatchQueryDetailResponse(BaseModel):
    # ... existing fields ...
    pct_drop_threshold: float | None = None
    alert_cooldown_hours: int
    is_all_time_low: bool = False  # computed, not stored
```

### Frontend TypeScript Types Extension
```typescript
// frontend/src/types/api.ts - add to existing interfaces
export interface WatchQueryResponse {
  // ... existing fields ...
  pct_drop_threshold: number | null;
  alert_cooldown_hours: number;
}

export interface WatchQueryDetailResponse {
  // ... existing fields ...
  pct_drop_threshold: number | null;
  alert_cooldown_hours: number;
  is_all_time_low: boolean;
}

export interface WatchQueryCreate {
  // ... existing fields ...
  pct_drop_threshold?: number | null;
  alert_cooldown_hours?: number;
}

export interface WatchQueryUpdate {
  // ... existing fields ...
  pct_drop_threshold?: number | null;
  alert_cooldown_hours?: number;
}
```

### All-Time Low Badge in QueryCard
```tsx
// In QueryCard.tsx, after the "Below threshold" badge
{detail?.is_all_time_low && (
  <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30">
    All-Time Low
  </Badge>
)}
```

### QueryFormDialog New Fields
```tsx
{/* Percentage Drop Threshold - optional */}
<div className="space-y-2">
  <Label htmlFor="query-pct-drop">Price Drop Alert (%)</Label>
  <Input
    id="query-pct-drop"
    type="text"
    inputMode="decimal"
    placeholder="e.g. 10 (leave empty to disable)"
    value={pctDrop}
    onChange={(e) => setPctDrop(e.target.value)}
  />
  <p className="text-xs text-muted-foreground">
    Alert when price drops this % below 30-day average
  </p>
</div>

{/* Alert Cooldown */}
<div className="space-y-2">
  <Label htmlFor="query-cooldown">Alert Cooldown (hours)</Label>
  <Input
    id="query-cooldown"
    type="number"
    min="0"
    value={cooldownHours}
    onChange={(e) => setCooldownHours(e.target.value)}
  />
  <p className="text-xs text-muted-foreground">
    Suppress repeat alerts within this time window
  </p>
</div>
```

## Key Implementation Details

### Repository Layer Changes
The `update_watch_query` function in `repositories/watch_query.py` has an `allowed_fields` set that must be updated:
```python
allowed_fields = {"name", "threshold_cents", "is_active", "schedule", "pct_drop_threshold", "alert_cooldown_hours"}
```

### create_watch_query Must Pass New Fields
The `create_watch_query` repository function and the `create` API endpoint must forward `pct_drop_threshold` and `alert_cooldown_hours` to the `WatchQuery` constructor.

### All-Time Low Computation Location
The `is_all_time_low` field is computed in the `GET /watch-queries/{id}` endpoint (the detail endpoint in `api/watch_queries.py`), NOT stored in the database. This keeps the data model simple and ensures correctness as new scrape results arrive.

### Cooldown Check Location
The cooldown check belongs at the TOP of the `for sr in scrape_results` loop in `evaluate_alerts_for_job`, before any `should_fire_alert` or percentage check. If the query is within cooldown, skip all alert evaluation for that scrape job entirely. This is a per-query check, not per-result, so it can be hoisted outside the loop for efficiency.

### Minimum Samples for Rolling Average
Use a minimum of 3 scrape results within the 30-day window before evaluating the percentage drop. This prevents false positives on new queries. If fewer than 3 samples exist, skip the percentage alert silently (do not error).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | backend/tests/conftest.py (in-memory SQLite) |
| Quick run command | `cd backend && python -m pytest tests/services/test_alert_service.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ALERT-05 | Pct drop alert fires when price is X% below 30-day avg | unit | `pytest tests/services/test_alert_service.py::TestPctDropAlert -x` | Wave 0 |
| ALERT-05 | Rolling average query returns correct avg and count | unit | `pytest tests/repositories/test_scrape_result.py::TestRollingAvg -x` | Wave 0 |
| ALERT-05 | Pct drop alert skipped when fewer than 3 samples | unit | `pytest tests/services/test_alert_service.py::TestPctDropAlert::test_insufficient_samples -x` | Wave 0 |
| ALERT-06 | All-time low detected correctly | unit | `pytest tests/repositories/test_scrape_result.py::TestAllTimeLow -x` | Wave 0 |
| ALERT-06 | is_all_time_low=true in detail response when current is lowest | integration | `pytest tests/api/test_watch_queries.py::test_detail_all_time_low -x` | Wave 0 |
| ALERT-07 | Alert suppressed within cooldown window | unit | `pytest tests/services/test_alert_service.py::TestCooldown -x` | Wave 0 |
| ALERT-07 | Alert fires after cooldown expires | unit | `pytest tests/services/test_alert_service.py::TestCooldown::test_cooldown_expired -x` | Wave 0 |
| ALERT-07 | Cooldown=0 disables cooldown | unit | `pytest tests/services/test_alert_service.py::TestCooldown::test_cooldown_disabled -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/services/test_alert_service.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/services/test_alert_service.py::TestPctDropAlert` -- new test class for percentage drop logic
- [ ] `tests/services/test_alert_service.py::TestCooldown` -- new test class for cooldown logic
- [ ] `tests/repositories/test_scrape_result.py::TestRollingAvg` -- new test class for rolling average repo function
- [ ] `tests/repositories/test_scrape_result.py::TestAllTimeLow` -- new test class for all-time min query

## Open Questions

1. **Alert type distinction in the `alerts` table**
   - What we know: Currently alerts have no `alert_type` column -- they're all threshold-based.
   - What's unclear: Should we add an `alert_type` field (e.g., "threshold", "pct_drop") so the alert log can show WHY the alert fired?
   - Recommendation: Add a nullable `alert_type` column (VARCHAR, default "threshold") to the `alerts` table in the same migration. This is low cost and makes the alert log more informative. Existing alerts get the default "threshold" value.

2. **Cooldown = 0 means disabled or means "no gap"?**
   - What we know: The requirement says "configurable time window (default 24h)".
   - What's unclear: Should 0 mean "alerts always fire (no cooldown)" or be rejected as invalid?
   - Recommendation: Treat `alert_cooldown_hours = 0` as "cooldown disabled, alerts always fire". This is the most intuitive behavior and allows users to opt out of cooldown entirely.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of all files listed above
- SQLAlchemy 2.x async documentation for `func.avg()`, `func.min()`, `func.max()` aggregation patterns
- Alembic documentation for `op.add_column` with `server_default` on existing tables

### Secondary (MEDIUM confidence)
- SQLite documentation for ADD COLUMN constraints (nullable or default required)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries, extending existing patterns
- Architecture: HIGH - clear extension points identified in existing code
- Pitfalls: HIGH - all pitfalls verified against actual codebase patterns
- SQL queries: HIGH - standard SQLAlchemy aggregation, verified against model schema

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable domain, no external API dependencies)
