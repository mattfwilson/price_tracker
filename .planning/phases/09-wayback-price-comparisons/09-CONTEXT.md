# Phase 9: Wayback Price Comparisons - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Add contextual price history stats to the watch query detail view (QuerySheet / ListingRow) — prices 30 and 90 days ago with comparison dates, 30-day and 90-day rolling averages with sample counts, a good/bad deal indicator per listing, and all-time high alongside the existing all-time low. All stats are per-listing (per retailer URL), embedded in the existing detail endpoint response.

No new pages or routes — this is a data and UI enrichment of the existing detail slide-over.

</domain>

<decisions>
## Implementation Decisions

### ListingRow Layout
- **D-01:** Stats are displayed in a compact second row directly below the existing price/delta/badge line.
  - Format: `30d: $51.99 (Mar 12) · 90d: $53.49 (Dec 23) · avg $50.12 (18 pts)  ✓ Good deal`
  - All stats and the good deal indicator live on this single compact row.
  - When fields are absent (e.g., no 30d data point found), omit that segment from the row gracefully.

### All-Time High/Low Scope
- **D-02:** All-time high and all-time low are **per-listing** (per retailer URL), not per watch query.
  - Each retailer URL independently tracks its own all-time high and all-time low.
  - These appear in the stats row (or a sub-element alongside it), not on the QuerySheet header.
  - New per-URL repo queries needed — `get_all_time_min_price` exists at query level; add per-URL variants.

### Good Deal Indicator
- **D-03:** Icon + text badge using the existing `Badge` component style (like the `[Lowest]` badge).
  - **Good deal:** green `✓ Good deal` badge — shown when current price < 90-day rolling average.
  - **Above average:** red `↑ Above avg` badge — shown when current price ≥ 90-day rolling average.
  - **Suppressed:** hide the badge entirely when 90-day average is unavailable (< 3 data points in window). No "N/A" or "Not enough data" label.

### API Delivery
- **D-04:** Wayback stats are embedded directly in `RetailerUrlWithLatest` within the existing `GET /watch-queries/{id}` detail endpoint response. Single round-trip — stats arrive alongside the listing data.
  - New fields added to `RetailerUrlWithLatest` schema (Pydantic model + TypeScript type).
  - Per-URL computation runs when the detail endpoint is called.

### Rolling Average Suppression
- **D-05:** Averages (30-day and 90-day) are suppressed (not shown) when sample count < 3 for that window. Applies to both the stats row display and the good deal indicator. This matches WAYBACK-02 exactly.

### Claude's Discretion
- Exact Tailwind classes and spacing for the compact stats row
- Whether 30d ago / 90d ago prices fall back to the nearest available record or use exact-day lookup — pick the approach that gives the most useful "closest to N days ago" result
- Field naming convention for the new wayback fields in the Pydantic schema and TypeScript types
- Loading skeleton treatment for the stats row while detail data fetches

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — WAYBACK-01 through WAYBACK-04

### Project constraints
- `.planning/PROJECT.md` — Stack (FastAPI backend, React frontend, SQLite, local-only), prices as integer cents

### Existing data layer (read before adding fields)
- `backend/app/schemas/watch_query.py` — `RetailerUrlWithLatest` (add wayback fields here), `WatchQueryDetailResponse` (all-time low is currently query-level here — new per-URL fields go on `RetailerUrlWithLatest`)
- `backend/app/repositories/scrape_result.py` — `get_rolling_avg_price()` (per-URL, already exists), `get_all_time_min_price()` (query-level — add per-URL variants for phase 9)
- `backend/app/api/watch_queries.py` — detail endpoint where new per-URL queries must be called

### Existing frontend patterns
- `frontend/src/components/query/ListingRow.tsx` — add compact stats row below existing price/delta line
- `frontend/src/components/query/QuerySheet.tsx` — renders ListingRow; no changes expected here
- `frontend/src/types/api.ts` — add wayback fields to `RetailerUrlWithLatest` TypeScript type
- `.planning/phases/06-price-history-visualization-polish/06-CONTEXT.md` — established patterns: price formatting via `formatPrice()`, delta direction, Badge component usage
- `.planning/phases/07-advanced-alert-enhancements/07-CONTEXT.md` — alert service already uses `get_rolling_avg_price()` for 30-day avg; phase 9 also needs 90-day avg

### Prior phase context
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — prices as integer cents throughout

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/repositories/scrape_result.py` — `get_rolling_avg_price(session, retailer_url_id, window_days)` already exists; call with `window_days=30` and `window_days=90`
- `frontend/src/components/ui/badge.tsx` — `Badge` component with variant support; good deal indicator reuses same pattern as `[Lowest]` badge in ListingRow
- `frontend/src/lib/format.ts` — `formatPrice()` handles cents→dollars display for all wayback price values

### Established Patterns
- All prices from API are integer cents — display via `formatPrice(price_cents)`
- TanStack Query detail hook at `frontend/src/hooks/use-watch-queries.ts` — no new hooks needed, wayback stats arrive in the same response
- Tailwind CSS v4 with dark mode support — stats row inherits theme automatically
- shadcn/ui `Badge` with `bg-emerald-500/15 text-emerald-400 border-emerald-500/30` pattern for green badges (copy from `[Lowest]`); red variant uses `bg-red-500/15 text-red-400 border-red-500/30`

### Integration Points
- `backend/app/api/watch_queries.py` detail endpoint → call per-URL wayback queries for each `retailer_url` in the response
- `backend/app/schemas/watch_query.py` `RetailerUrlWithLatest` → add optional wayback fields (price_30d_cents, date_30d, price_90d_cents, date_90d, avg_30d_cents, avg_30d_count, avg_90d_cents, avg_90d_count, all_time_low_cents, all_time_high_cents) — all optional/nullable
- `frontend/src/types/api.ts` → add matching optional fields to `RetailerUrlWithLatest`
- `frontend/src/components/query/ListingRow.tsx` → add stats row after existing price/delta line

</code_context>

<specifics>
## Specific Ideas

- User confirmed the compact stats row mockup:
  ```
  product_name
  $49.99  ↓ -2.1%  [Lowest]
  30d: $51.99 (Mar 12) · 90d: $53.49 (Dec 23) · avg $50.12 (18 pts)  ✓ Good deal
                                                       [View history]
  ```
- Good deal badge matches the `[Lowest]` badge visual style — use the same Badge component with appropriate color variants

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-wayback-price-comparisons*
*Context gathered: 2026-03-23*
