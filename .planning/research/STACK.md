# Stack Research

**Domain:** Price tracker v1.1 -- scrape health monitoring, wayback price comparisons, multi-product fuzzy matching
**Researched:** 2026-03-22
**Confidence:** HIGH

## Existing Stack (validated in v1.0 -- DO NOT change)

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | >=0.135.0 | Backend API |
| SQLAlchemy (async) | >=2.0.48 | ORM + async SQLite |
| aiosqlite | >=0.22.0 | Async SQLite driver |
| Alembic | >=1.18.0 | Database migrations |
| Patchright (Playwright fork) | >=1.48.0 | Headless browser scraping |
| APScheduler 3.x | >=3.11.0 | Background job scheduling |
| Tenacity | >=9.0.0 | Retry logic |
| httpx | >=0.28.0 | Async HTTP client |
| React 19 + Vite 8 | latest | Frontend framework + build |
| TanStack Query 5 | >=5.91.2 | Data fetching/caching |
| Recharts 3 | >=3.8.0 | Charts |
| shadcn/ui + Tailwind 4 | latest | UI components |
| Zod 4 | >=4.3.6 | Schema validation |
| Lucide React | >=0.577.0 | Icons |

## Recommended Stack Additions

### Backend -- One New Dependency

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| rapidfuzz | >=3.12.0 | Fuzzy string matching for product title deduplication | MIT license (thefuzz is GPL -- non-starter). C++ core makes it 16x faster than thefuzz. Provides `token_sort_ratio` and `token_set_ratio` scorers ideal for product names where word order and extra words vary across retailers. `process.cdist` computes NxN similarity matrices efficiently for batch matching. Zero transitive runtime dependencies. The standard production choice for Python fuzzy matching. |

**This is the only new pip dependency needed for all three features.**

### Backend -- Features Using Existing Stack Only

| Feature | Implementation Approach | Why No New Library |
|---------|------------------------|-------------------|
| Scrape health dashboard | SQLAlchemy aggregate queries on existing `scrape_jobs` table | ScrapeJob already tracks `status`, `error_message`, `started_at`, `completed_at`. Health metrics (success rate, consecutive failures, last success) are pure SQL aggregations. No new library needed. |
| Wayback price comparisons | Date-windowed SQLAlchemy queries on existing `scrape_results` table | The repository already has `get_rolling_avg_price()` with a `window_days` parameter. Wayback stats ("30 days ago: $X", "90 days ago: $Y") are additional date-filtered queries on `price_cents` + `created_at`. Same pattern, different windows. |
| Product match group storage | New Alembic migration + SQLAlchemy models | Match groups are relational data (group -> members). Standard SQLAlchemy models and foreign keys. |

### Frontend -- No New npm Dependencies Needed

| Feature | Implementation Approach | Why No New Library |
|---------|------------------------|-------------------|
| Health dashboard table | shadcn `<Table>` component (already installed at `frontend/src/components/ui/table.tsx`) | Simple sortable table for per-URL health stats. For a personal tool with 10-50 tracked URLs, manual sort state is sufficient. TanStack Table would be overkill. |
| Health status indicators | Existing `<Badge>` + `lucide-react` icons + existing `StatusDot` component | Color-coded indicators for health status. The project already has a StatusDot component and Badge primitives. |
| Wayback price display | Inline text in existing detail views | "30 days ago: $X" is text annotation, not a chart. Render using existing `format.ts` price formatting utilities. |
| Product match groups | Existing `<Card>` + `<Table>` components | Grouped cards showing cross-retailer comparisons. No new component primitives needed. |
| Health trend sparklines (stretch) | Recharts mini `<LineChart>` | Recharts 3 is already installed. Tiny inline success/failure trend chart is a small Recharts usage. |

## Installation

```bash
# Backend -- single new dependency
# Add to pyproject.toml [project] dependencies:
#   "rapidfuzz>=3.12.0",

cd backend
pip install "rapidfuzz>=3.12.0"
```

No frontend installation changes.

## rapidfuzz Integration Details

### Why rapidfuzz (not alternatives)

For matching product titles like "Samsung Galaxy S24 Ultra 256GB Black" (Amazon) vs "Galaxy S24 Ultra Samsung - 256GB" (Best Buy):

- **`fuzz.token_sort_ratio`**: Splits into tokens, sorts alphabetically, then compares. Handles reordered words.
- **`fuzz.token_set_ratio`**: Handles one title having extra words the other lacks (e.g., color names, "with MagSafe").
- **`process.cdist`**: Computes full NxN similarity matrix across all tracked product titles in one call. For 100 products, that is 10,000 comparisons -- takes milliseconds with C++ backend.

### Recommended Usage Pattern

```python
from rapidfuzz import fuzz, process

# Compare two product titles
score = fuzz.token_sort_ratio(
    "Samsung Galaxy S24 Ultra 256GB",
    "Galaxy S24 Ultra Samsung 256GB"
)
# Returns ~95.0

# Batch: find all matches above threshold across all titles
from rapidfuzz.process import cdist
import numpy as np

titles = [r.product_name for r in all_latest_results]
scores = cdist(titles, titles, scorer=fuzz.token_sort_ratio)
# scores[i][j] = similarity between titles[i] and titles[j]
# Group pairs where scores[i][j] >= threshold
```

### Match Threshold Guidance

| Score | Interpretation | Action |
|-------|---------------|--------|
| >=90 | Almost certainly same product (formatting differences only) | Auto-group |
| 75-89 | Likely same product (different retailer naming conventions) | Auto-group with lower confidence flag |
| <75 | Different products | Do not group |

Start with threshold of 80. Expose as a setting in `app_settings` (the model already exists).

### When to Run Matching

Run as a post-scrape batch job, not on every individual scrape:
1. After a scrape job completes, check if any product_name changed
2. If yes, re-run matching for that watch query's retailer URLs
3. Update `product_match_members` table

This avoids expensive NxN comparisons on every scrape when titles have not changed.

## Database Schema Additions

New tables via Alembic migrations (no new DB engine or library):

### New: `product_matches` table

Represents a group of retailer URLs that resolve to the same product.

```
product_matches:
  id              INTEGER PRIMARY KEY
  canonical_name  TEXT        -- best/longest product name from the group
  created_at      DATETIME
  updated_at      DATETIME
```

### New: `product_match_members` table

Links retailer URLs to their match group.

```
product_match_members:
  id                INTEGER PRIMARY KEY
  product_match_id  INTEGER FK -> product_matches.id
  retailer_url_id   INTEGER FK -> retailer_urls.id  (UNIQUE constraint)
  product_name      TEXT        -- raw title from this retailer
  similarity_score  REAL        -- score vs canonical name
  created_at        DATETIME
```

### Existing tables -- already sufficient for health + wayback

**`scrape_jobs`** already has: `status` (pending/running/completed/failed), `error_message`, `started_at`, `completed_at`, `watch_query_id`. Derived health metrics:
- Success rate: `COUNT(status='completed') / COUNT(*)` grouped by watch_query_id
- Consecutive failures: ordered window on recent jobs
- Last success: `MAX(completed_at) WHERE status='completed'`

**`scrape_results`** already has: `price_cents`, `created_at`, `retailer_url_id`. Wayback queries:
- "30 days ago": price from the result closest to `now() - 30 days`
- "90 days ago": price from the result closest to `now() - 90 days`
- Historical average: already implemented in `get_rolling_avg_price()`

### Recommended New Indexes

```sql
-- Speed up health aggregation queries
CREATE INDEX ix_scrape_jobs_wq_status ON scrape_jobs(watch_query_id, status);

-- Speed up wayback price lookups (date-range scans per URL)
CREATE INDEX ix_scrape_results_url_created ON scrape_results(retailer_url_id, created_at);

-- Speed up "all results in last N days" scans
CREATE INDEX ix_scrape_results_created ON scrape_results(created_at);
```

The `retailer_url_id + created_at` composite index is the most critical -- it makes wayback queries O(log n) instead of full table scans.

## Alternatives Considered

| Recommended | Alternative | Why Not Alternative |
|-------------|-------------|---------------------|
| rapidfuzz | thefuzz (fuzzywuzzy) | GPL license. Slower (pure Python fallback). Unmaintained compared to rapidfuzz. rapidfuzz is a strict superset with compatible API. |
| rapidfuzz | python-Levenshtein | Only provides edit distance, not token-based scorers. Product names need token_sort_ratio for reordered words. |
| rapidfuzz | spaCy / sentence-transformers | 500MB+ model downloads for NLP. Massive overkill for fuzzy string matching of product titles. Would dominate install size and startup time. |
| rapidfuzz | Similarity API (SaaS) | External API dependency for a local-only tool. Overkill for <1000 product titles. |
| SQLAlchemy aggregates for health | Materialized views / denormalized health columns | Premature optimization. For a personal tool with hundreds of scrape jobs, aggregate queries on indexed columns complete in <10ms. Add denormalization only if profiling shows it is needed. |
| shadcn Table (manual sort) | TanStack Table (@tanstack/react-table) | New dependency for a table with 10-50 rows. Manual sort state in a React component is ~15 lines of code. Add TanStack Table only if requirements grow to filtering + pagination. |
| Recharts for sparklines | No chart / just numbers | Numbers alone (success rate %, consecutive failures count) are sufficient for MVP. Sparklines are a stretch goal enhancement. |

## What NOT to Add

| Avoid | Why | Do Instead |
|-------|-----|------------|
| numpy / pandas for matching | rapidfuzz's `cdist` returns a list-of-lists that works fine without numpy. Adding numpy for one function is wasteful (25MB+ install). | Use rapidfuzz's built-in matrix output |
| A separate health/metrics DB (InfluxDB, Prometheus) | This is observability of a personal tool, not production monitoring. The scrape_jobs table IS the metrics store. | Query scrape_jobs with SQLAlchemy |
| Redis for caching health stats | Single user, local app. TanStack Query already caches API responses on the frontend with configurable stale time. | Set `staleTime: 30_000` on health queries in TanStack Query |
| @tanstack/react-table | The health table is small and simple. Adding a full table library for <50 rows is over-engineering. | shadcn `<Table>` with `useState` for sort |
| chart.js / visx / nivo | Recharts is already installed and working. Adding a second charting library creates maintenance burden. | Recharts for any new chart needs |
| Web Workers for fuzzy matching | Matching runs on the backend in Python, not in the browser. The frontend just displays results. | Server-side matching with rapidfuzz |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| rapidfuzz >=3.12.0 | Python >=3.9 | Project requires >=3.10, fully compatible |
| rapidfuzz >=3.12.0 | SQLAlchemy >=2.0 | No interaction -- rapidfuzz operates on Python strings extracted from query results |
| rapidfuzz >=3.12.0 | No C compiler needed | Ships pre-built wheels for macOS (darwin), Linux, Windows |

## API Endpoint Patterns (for reference)

New endpoints needed, all using existing FastAPI patterns:

```
GET  /api/health/urls           -- per-URL health summary (success rate, last success, consecutive failures)
GET  /api/health/urls/{id}      -- detailed health for one URL (recent job history)
GET  /api/prices/wayback/{retailer_url_id}?days=30,90  -- price at N days ago
GET  /api/matches                -- all product match groups
POST /api/matches/recompute      -- trigger re-matching (admin action)
```

All follow existing patterns: async route handlers, `Depends(get_db)` for sessions, Pydantic response schemas.

## Sources

- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) -- MIT license, C++ core, API documentation
- [RapidFuzz 3.14.3 documentation](https://rapidfuzz.github.io/RapidFuzz/) -- current stable version, scorer APIs (token_sort_ratio, token_set_ratio, cdist)
- [2025 Fuzzy Matching Benchmarks](https://similarity-api.com/blog/speed-benchmarks) -- rapidfuzz vs thefuzz performance (16x faster confirmed)
- [thefuzz GitHub](https://github.com/seatgeek/thefuzz) -- GPL license confirmed, less active maintenance
- [shadcn/ui Table docs](https://ui.shadcn.com/docs/components/radix/table) -- component API, confirmed already installed in project
- [shadcn/ui Data Table docs](https://ui.shadcn.com/docs/components/radix/data-table) -- TanStack Table integration pattern (evaluated and deferred)
- Existing codebase analysis:
  - `backend/app/models/scrape_job.py` -- confirms status/error_message/timestamps already tracked
  - `backend/app/repositories/scrape_result.py` -- confirms `get_rolling_avg_price()` pattern exists
  - `frontend/src/components/ui/table.tsx` -- confirms shadcn Table already installed
  - `frontend/src/components/dashboard/StatusDot.tsx` -- confirms health indicator component exists
  - `frontend/src/lib/format.ts` -- confirms price formatting utilities exist

---
*Stack research for: price tracker v1.1 -- scrape health, wayback prices, fuzzy matching*
*Researched: 2026-03-22*
