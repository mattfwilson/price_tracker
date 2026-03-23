# Architecture Research

**Domain:** Price tracker v1.1 -- scrape health, wayback price comparisons, fuzzy product matching
**Researched:** 2026-03-22
**Confidence:** HIGH

## Existing Architecture Summary

The current system is a single-process monolith with clean layered separation:

```
Frontend (React + TanStack Query + shadcn/ui)
    |
    | REST API + SSE
    v
API Layer (FastAPI routers: watch_queries, scrapes, alerts)
    |
    v
Service Layer (scrape_service, alert_service, scheduler)
    |
    v
Repository Layer (scrape_result, watch_query, alert repos)
    |
    v
Models (SQLAlchemy async ORM)
    |
    v
SQLite (WAL mode, single file)
```

**Existing entities:**
- `watch_queries` -- user-created targets with threshold, schedule, alert cooldown
- `retailer_urls` -- belongs to watch_query, the URLs to scrape
- `scrape_jobs` -- one per scheduled/on-demand run, has status (success/failed/partial_success) and error_message
- `scrape_results` -- immutable price snapshots (product_name, price_cents, retailer_name, listing_url, created_at), belongs to retailer_url and scrape_job
- `alerts` -- triggered when price conditions are met
- `app_settings` -- key-value config store

**Critical observation for Feature 1:** `scrape_results` only stores SUCCESSFUL scrapes. When a URL fails, the only record is a concatenated error string on `scrape_job.error_message`. There is no per-URL failure tracking. This is the primary data gap.

**Critical observation for Feature 2:** `scrape_results` already has all the price history data needed. The repository already has `get_rolling_avg_price()` and `get_all_time_min_price()`. Wayback stats are a computation problem, not a storage problem.

**Critical observation for Feature 3:** Product names come from scrape results and are retailer-specific strings. Different retailers format the same product name differently. Matching requires fuzzy comparison across all retailer_urls, not just within a single watch_query.

## Feature 1: Scrape Health Dashboard

### The Data Gap

When `scrape_service.run_scrape_job()` processes each URL, failures are:
1. Counted in local `failures` variable
2. Appended to an `error_messages` list
3. Concatenated into `scrape_job.error_message`

This means per-URL failure history is lost. You cannot query "how many times did URL X fail in the last 7 days?" or "what was the last error for URL X?"

### Recommended Approach: New `scrape_attempts` Table

Do NOT retrofit `scrape_results` with error rows (pollutes every price query) or parse `scrape_job.error_message` strings (fragile, lossy). Add a dedicated table.

### New Model: `ScrapeAttempt`

```python
class ScrapeAttempt(Base):
    __tablename__ = "scrape_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    retailer_url_id: Mapped[int] = mapped_column(ForeignKey("retailer_urls.id"))
    scrape_job_id: Mapped[int] = mapped_column(ForeignKey("scrape_jobs.id"))
    status: Mapped[str] = mapped_column(String(20))  # "success" | "error"
    error_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

**Integration point:** Modify `scrape_service.run_scrape_job()` to create a `ScrapeAttempt` row for EVERY URL processed. The try/except block already distinguishes success from failure -- add one row in each branch. This is a ~10-line change.

### New API Endpoint

```
GET /scrape-health
```

Response schema:

```python
class UrlHealthResponse(BaseModel):
    retailer_url_id: int
    url: str
    watch_query_id: int
    watch_query_name: str
    total_attempts: int         # last 30 days
    success_count: int
    failure_count: int
    success_rate: float         # 0.0 - 1.0
    last_success_at: datetime | None
    last_failure_at: datetime | None
    consecutive_failures: int
    last_error_type: str | None
    last_error_message: str | None

class HealthSummaryResponse(BaseModel):
    total_urls: int
    healthy_count: int          # success_rate > 0.8
    degraded_count: int         # 0.5 - 0.8
    failing_count: int          # < 0.5
    never_succeeded_count: int

class ScrapeHealthResponse(BaseModel):
    urls: list[UrlHealthResponse]
    summary: HealthSummaryResponse
```

**Computation:** Query-time aggregation from `scrape_attempts`. SQLite handles this fine for a personal tool. No caching or materialized views needed.

**Consecutive failure count:** Query the most recent N attempts for a URL ordered by `created_at DESC`, count leading "error" rows until the first "success".

### Frontend Components

| Component | New/Modified | Purpose |
|-----------|-------------|---------|
| `ScrapeHealthPage` | NEW | Top-level page at `/health` route |
| `HealthTable` | NEW | Sortable table of URL health metrics |
| `HealthBadge` | NEW | Color-coded badge (green/yellow/red) based on success_rate |
| `Header` | MODIFIED | Add nav link to health page |
| `ListingRow` | MODIFIED | Show health indicator per URL in detail view |

### Data Flow

```
APScheduler triggers scrape
    |
    v
scrape_service.run_scrape_job()
    |-- for each retailer_url:
    |     |-- attempt scrape
    |     |-- CREATE scrape_attempt (success or error)  <-- NEW
    |     |-- if success: CREATE scrape_result (unchanged)
    |
    v
Frontend: GET /scrape-health
    |
    v
Repository: aggregate scrape_attempts per retailer_url (SQL GROUP BY + window)
    |
    v
Response: ScrapeHealthResponse
```

## Feature 2: Wayback Price Comparisons

### No New Tables Needed

All data exists in `scrape_results`. This feature adds:
1. New repository query functions
2. Extended API response schema
3. New frontend display component

### New Repository Function

```python
async def get_wayback_stats(
    session: AsyncSession, retailer_url_id: int
) -> WaybackStats:
    """Price-at-date snapshots and averages for a retailer URL."""
    # For each period (7d, 30d, 90d):
    #   SELECT * FROM scrape_results
    #   WHERE retailer_url_id = ? AND created_at <= (now - period)
    #   ORDER BY created_at DESC LIMIT 1
    #
    # This gives the most recent known price at or before the target date.
    # Also compute: avg over 30d, avg over 90d, all-time avg
```

### API Integration: Extend Existing Detail Endpoint

**Recommended:** Add wayback data to `GET /watch-queries/{id}` response. The detail handler already loops through retailer_urls fetching per-URL data. Adding wayback queries in that same loop avoids N+1 frontend requests.

Do NOT create a separate `GET /retailer-urls/{id}/wayback` endpoint -- it would require one request per URL from the frontend.

### New Schema Additions

```python
class WaybackSnapshot(BaseModel):
    period_label: str           # "7d", "30d", "90d"
    price_cents: int | None     # null if no data that far back
    snapshot_date: datetime | None
    vs_current_cents: int | None   # current - snapshot
    vs_current_pct: float | None

class WaybackStats(BaseModel):
    snapshots: list[WaybackSnapshot]
    avg_30d_cents: int | None
    avg_90d_cents: int | None
    avg_all_time_cents: int | None
    current_vs_avg_30d_pct: float | None  # positive = above average
```

Add `wayback: WaybackStats | None` to `RetailerUrlWithLatest` (in `schemas/watch_query.py`).

### Frontend Components

| Component | New/Modified | Purpose |
|-----------|-------------|---------|
| `WaybackStats` | NEW | Display price comparison chips/badges per listing |
| `QuerySheet` | MODIFIED | Embed WaybackStats in detail view per listing |
| `PriceChart` | MODIFIED | Optionally show average reference lines |

### Data Flow

```
Frontend: GET /watch-queries/{id}
    |
    v
API: get_query() handler
    |-- for each retailer_url:
    |     |-- get_latest_scrape_result() (existing)
    |     |-- get_wayback_stats()        (NEW)
    |
    v
Response: WatchQueryDetailResponse with wayback per URL
```

## Feature 3: Multi-Product Fuzzy Matching

### Design Decisions

**When does matching happen?** Background job, not on-demand. Fuzzy matching across all product names is O(N^2). Even with modest data, doing this per API request adds latency and is wasteful since matches change only when new scrape results arrive.

**What gets matched?** The latest `product_name` from `scrape_results` for each `retailer_url`, compared across ALL watch queries (not just within one).

**Where are matches stored?** New tables. Pre-computed groups served from the API.

### Matching Library: RapidFuzz

Use `rapidfuzz` -- a C++ accelerated fuzzy matching library. It is 10-100x faster than `thefuzz` and uses MIT license (vs GPL). For product names, use `token_sort_ratio` which handles word reordering common across retailers (e.g., "Samsung Galaxy S24 256GB" vs "Galaxy S24 Samsung 256GB Black").

**Confidence: HIGH** -- RapidFuzz is the established standard for Python fuzzy matching.

### New Models

```python
class ProductMatchGroup(Base):
    __tablename__ = "product_match_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

class ProductMatchMember(Base):
    __tablename__ = "product_match_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("product_match_groups.id"))
    retailer_url_id: Mapped[int] = mapped_column(
        ForeignKey("retailer_urls.id"), unique=True
    )
    product_name: Mapped[str] = mapped_column(String(500))
    similarity_score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

**Design rationale:**
- `retailer_url_id` has a unique constraint -- each URL belongs to at most one group
- `canonical_name` is the longest/most descriptive name in the group (longer retailer names tend to be more specific)
- `similarity_score` is stored for UI transparency and debugging

### New Service: `match_service.py`

```python
async def run_product_matching(session: AsyncSession) -> None:
    """Recompute product match groups from latest scrape results."""
    # 1. Get latest product_name for each retailer_url that has results
    # 2. Normalize: lowercase, strip trademark symbols, trim whitespace
    # 3. Pairwise comparison using rapidfuzz.fuzz.token_sort_ratio
    # 4. Cluster with threshold >= 80 (configurable via app_settings)
    # 5. Single-linkage clustering: if A~B and B~C, all three group together
    # 6. Upsert: delete stale groups, create new, update changed
```

**When to run:** Trigger from the scheduler after scrape jobs complete. Use a debounce (at most once per 10 minutes via APScheduler's `max_instances=1` and `coalesce=True`) to avoid redundant runs when multiple queries scrape in quick succession.

### New API Endpoints

```
GET /product-matches
  -> list[MatchGroupResponse]  (groups with members and latest prices)

GET /product-matches/{group_id}
  -> MatchGroupDetailResponse  (detailed group with price comparison)
```

### Frontend Components

| Component | New/Modified | Purpose |
|-----------|-------------|---------|
| `ProductMatchesPage` | NEW | Top-level page at `/matches` route |
| `MatchGroupCard` | NEW | Card showing group with cross-retailer price comparison |
| `MatchBadge` | NEW | Badge on listings indicating "matched with N others" |
| `QuerySheet` | MODIFIED | Show match indicator per listing row |
| `Header` | MODIFIED | Add nav link to matches page |

### Data Flow

```
Scrape job completes
    |
    v (scheduler triggers, debounced)
match_service.run_product_matching()
    |-- Query latest product_name per retailer_url
    |-- Normalize names
    |-- Pairwise rapidfuzz.fuzz.token_sort_ratio
    |-- Single-linkage cluster at >= 80% threshold
    |-- Upsert product_match_groups + members
    |
    v
Frontend: GET /product-matches
    |
    v
Response: groups with members, latest prices, cross-retailer comparison
```

## Complete Integration Map

### New Files

| File | Layer | Feature |
|------|-------|---------|
| `backend/app/models/scrape_attempt.py` | Model | Health |
| `backend/app/models/product_match.py` | Model | Matching |
| `backend/app/repositories/scrape_health.py` | Repository | Health |
| `backend/app/repositories/wayback.py` | Repository | Wayback |
| `backend/app/repositories/product_match.py` | Repository | Matching |
| `backend/app/services/match_service.py` | Service | Matching |
| `backend/app/api/health.py` | API router | Health |
| `backend/app/api/product_matches.py` | API router | Matching |
| `backend/app/schemas/health.py` | Schema | Health |
| `backend/app/schemas/wayback.py` | Schema | Wayback |
| `backend/app/schemas/product_match.py` | Schema | Matching |
| `frontend/src/pages/ScrapeHealthPage.tsx` | Page | Health |
| `frontend/src/pages/ProductMatchesPage.tsx` | Page | Matching |
| `frontend/src/components/health/HealthTable.tsx` | Component | Health |
| `frontend/src/components/health/HealthBadge.tsx` | Component | Health |
| `frontend/src/components/wayback/WaybackStats.tsx` | Component | Wayback |
| `frontend/src/components/matches/MatchGroupCard.tsx` | Component | Matching |

### Modified Files

| File | Change | Feature |
|------|--------|---------|
| `backend/app/services/scrape_service.py` | Add scrape_attempt creation in `run_scrape_job` | Health |
| `backend/app/services/scheduler.py` | Add match_service trigger after scrape | Matching |
| `backend/app/api/watch_queries.py` | Add wayback stats to detail response | Wayback |
| `backend/app/schemas/watch_query.py` | Add `wayback` field to `RetailerUrlWithLatest` | Wayback |
| `backend/app/models/__init__.py` | Register new models | All |
| `frontend/src/types/api.ts` | Add new response types | All |
| `frontend/src/App.tsx` | Add `/health` and `/matches` routes | Health, Matching |
| `frontend/src/components/layout/Header.tsx` | Add nav links | Health, Matching |
| `frontend/src/components/query/QuerySheet.tsx` | Show wayback stats + match indicators | Wayback, Matching |
| `frontend/src/components/query/ListingRow.tsx` | Show health indicator per URL | Health |

### Database Migration

Single migration adding three tables (all additive, no changes to existing tables):

```sql
CREATE TABLE scrape_attempts (
    id INTEGER PRIMARY KEY,
    retailer_url_id INTEGER NOT NULL REFERENCES retailer_urls(id),
    scrape_job_id INTEGER NOT NULL REFERENCES scrape_jobs(id),
    status VARCHAR(20) NOT NULL,
    error_type VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_scrape_attempts_url_date ON scrape_attempts(retailer_url_id, created_at);

CREATE TABLE product_match_groups (
    id INTEGER PRIMARY KEY,
    canonical_name VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_match_members (
    id INTEGER PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES product_match_groups(id),
    retailer_url_id INTEGER NOT NULL REFERENCES retailer_urls(id) UNIQUE,
    product_name VARCHAR(500) NOT NULL,
    similarity_score REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_product_match_members_group ON product_match_members(group_id);
```

## Suggested Build Order

### Phase 1: Scrape Health Dashboard

**Why first:**
- Zero dependency on other features
- Introduces `scrape_attempts` which should start logging before more scrapes run untracked
- Immediate operational value -- shows which URLs are broken
- Informs Feature 3 -- health data reveals URLs with unreliable product names that would produce bad fuzzy matches

### Phase 2: Wayback Price Comparisons

**Why second:**
- Zero dependency on Phase 1 or 3
- No new tables -- pure read-only computation over existing data
- Lowest complexity of the three features
- Extends existing endpoint rather than adding new pages

### Phase 3: Multi-Product Fuzzy Matching

**Why last:**
- Most complex: new background job, fuzzy algorithm, clustering logic, two new tables
- Benefits from Phase 1 health data to identify unreliable URLs
- Most likely to need iterative tuning (threshold, normalization rules)
- Largest frontend surface area (new page, new components, modifications to existing views)

### Dependency Diagram

```
Phase 1 (Health)  ──────> Phase 3 (Matching) benefits from health data
                            ^
Phase 2 (Wayback) ──────> | (independent, but smaller scope done first)
```

No hard dependencies between features. The ordering is about risk management and incremental value delivery.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Storing Computed Health Stats in a Summary Table

**What people do:** Create a `url_health_summary` table with pre-computed success_rate and consecutive_failures, updated after each scrape.
**Why it's wrong:** For a personal tool with modest data, this adds write complexity and staleness risk. The summary drifts if an update is missed.
**Do this instead:** Compute on-demand from `scrape_attempts`. SQLite aggregation over hundreds of rows is sub-millisecond.

### Anti-Pattern 2: Running Fuzzy Matching in the API Request Path

**What people do:** Compute matches on `GET /product-matches` by running pairwise fuzzy comparison.
**Why it's wrong:** O(N^2) computation blocks the request. 100 URLs = 4,950 comparisons per request.
**Do this instead:** Pre-compute matches in a background job, serve stored groups from the API.

### Anti-Pattern 3: Adding Error Rows to scrape_results

**What people do:** Add a `status` column to `scrape_results` and insert error rows with null prices.
**Why it's wrong:** Pollutes every price query. The existing history, delta, average, and min-price queries all assume every row has a valid price. Every query would need `WHERE status = 'success'` guards.
**Do this instead:** Separate `scrape_attempts` table. Success data stays in `scrape_results` (immutable prices). Operational data stays in `scrape_attempts`.

### Anti-Pattern 4: Over-Normalizing Product Names

**What people do:** Strip everything except alphanumeric characters before fuzzy matching.
**Why it's wrong:** Removes meaningful differentiation. "iPhone 16 Pro 256GB" and "iPhone 16 128GB" would match too aggressively.
**Do this instead:** Light normalization only (lowercase, trim whitespace, remove trademark symbols). Let the 80% similarity threshold handle the rest. Start conservative and tune.

### Anti-Pattern 5: Separate Wayback API Endpoint Per URL

**What people do:** Create `GET /retailer-urls/{id}/wayback` and make N requests from the frontend.
**Why it's wrong:** N+1 request problem. A watch query with 5 URLs means 6 requests to load the detail view.
**Do this instead:** Embed wayback stats in the existing `GET /watch-queries/{id}` response, computed in the same per-URL loop.

## Sources

- Existing codebase analysis: models, repositories, services, API endpoints, schemas (all files read directly)
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) -- fuzzy matching library, performance benchmarks
- [RapidFuzz documentation](https://rapidfuzz.github.io/RapidFuzz/) -- API reference for token_sort_ratio

---
*Architecture research for: Price Tracker v1.1 feature integration*
*Researched: 2026-03-22*
