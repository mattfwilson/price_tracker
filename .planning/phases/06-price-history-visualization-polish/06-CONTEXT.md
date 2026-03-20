# Phase 6: Price History Visualization + Polish - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Interactive price history visualization (line chart + sortable table per listing) and dark mode toggle. History is accessible from the QuerySheet slide-over's listing rows. Dark mode adds a light theme alternative with a toggle — the current dark terminal palette becomes the "dark" mode.

</domain>

<decisions>
## Implementation Decisions

### History entry point
- Clicking "View history" on a listing row **replaces the slide-over content** with a history view for that listing
- A ← back button at the top returns to the listings view (no full close/reopen)
- History header shows: **product name · retailer domain** (e.g., "Sony WH-1000XM5 · amazon.com")
- If no scrape history exists yet: show an empty state message — "No history yet — trigger a scrape to start tracking." (don't keep the link disabled; allow discovery)

### Chart + table layout
- **Stacked layout:** chart on top, table below — single scroll, everything visible at once
- **Time range filter** (7d / 30d / 90d / all) sits above the chart as segmented buttons; applies to both chart and table simultaneously
- Chart: line chart with a horizontal dashed threshold line overlay (HIST-03)
- Table: date, price, delta columns — default sort newest-first; column headers are clickable to re-sort (HIST-04, HIST-05)

### Time range filtering
- **Frontend filtering:** fetch the full history once on view open, filter client-side when the user switches ranges — instant switching, no extra API calls per range change

### Claude's Discretion
- Dark mode implementation: keep current dark terminal palette as "dark" mode, add a light theme, wire up next-themes (already installed); toggle location and light theme aesthetic are Claude's call
- Chart library: Recharts (as specified in roadmap plans 06-01)
- Exact chart styling: line color, dot size, tooltip design, threshold line dash pattern
- Table sort icon treatment and active sort indicator
- Loading skeleton while history fetches

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — HIST-03 (line chart + threshold overlay), HIST-04 (sortable table, newest-first default), HIST-05 (time range filter: 7d/30d/90d/all), UI-02 (dark mode toggle)
- `.planning/PROJECT.md` — Stack constraints (React + Tailwind CSS frontend, local-only)

### Phase 5 context (existing UI patterns and integration points)
- `.planning/phases/05-dashboard-frontend/05-CONTEXT.md` — QuerySheet slide-over structure, ListingRow "View history" stub, established Tailwind/Radix/shadcn patterns, TanStack Query cache strategy

### Backend API
- `.planning/phases/03-api-watch-query-management/03-CONTEXT.md` — Price history endpoint: `GET /retailer-urls/{retailer_url_id}/history` returns newest-first records with price_cents, direction, pct_change, timestamp

### Prior data layer decisions
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — Prices stored as integer cents throughout; all display must convert (price_cents / 100 → "$X.XX")

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/query/QuerySheet.tsx` — Slide-over shell; history view replaces its inner content (add state: `selectedListingId: number | null` to toggle between listing list and history view)
- `frontend/src/components/query/ListingRow.tsx` — Has a disabled "View history" span — Phase 6 makes it an active click handler
- `frontend/src/hooks/use-watch-queries.ts` — TanStack Query patterns established; add `useListingHistory(retailerUrlId)` hook following same pattern
- `frontend/src/lib/format.ts` — `formatPrice()` already handles cents→dollars display

### Established Patterns
- All prices in API are integer cents — display via `formatPrice(price_cents)`
- Delta direction: `"new" | "higher" | "lower" | "unchanged"` → map with `deltaIcon()`
- Tailwind CSS v4 with custom theme variables (`--color-primary`, `--color-border`, etc.)
- `next-themes` is installed (v0.4.6) but not wired — Phase 6 sets up ThemeProvider and toggle
- shadcn/ui components available (`Badge`, `Separator`, `Sheet`, `Skeleton`, etc.)

### Integration Points
- `GET /retailer-urls/{retailer_url_id}/history` → fetch in `useListingHistory` hook
- `ListingRow.tsx` → "View history" click passes `url.id` up to `QuerySheet` to set selected listing
- `QuerySheet.tsx` → conditionally renders listing list OR history view based on `selectedListingId`
- `frontend/src/index.css` → add `.dark` theme overrides alongside existing dark palette (which becomes the default dark theme)
- App root → wrap with `ThemeProvider` from next-themes; add toggle button to `Header.tsx`

</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" moments — open to standard clean approaches for chart and table visual execution.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-price-history-visualization-polish*
*Context gathered: 2026-03-20*
