---
phase: 06-price-history-visualization-polish
plan: 01
subsystem: ui
tags: [recharts, react, line-chart, sortable-table, price-history, tanstack-query]

# Dependency graph
requires:
  - phase: 05-dashboard-frontend
    provides: QuerySheet, ListingRow, shadcn Table, TanStack Query hooks, format utils
  - phase: 03-api-watch-query-management
    provides: GET /retailer-urls/{id}/history endpoint
provides:
  - PriceHistoryView container with back navigation and loading/error/empty states
  - PriceChart line chart with threshold ReferenceLine overlay
  - PriceTable sortable table with date/price/delta columns
  - TimeRangeFilter segmented buttons (7d/30d/90d/all) with filterByRange utility
  - useListingHistory hook and retailerUrls.history() API method
  - HistoryRecord type definition
  - formatDate and formatChartDate utilities
affects: [06-02-dark-mode-polish]

# Tech tracking
tech-stack:
  added: [recharts]
  patterns: [slide-over content swapping via selectedListingId state, client-side time range filtering]

key-files:
  created:
    - frontend/src/components/history/PriceHistoryView.tsx
    - frontend/src/components/history/PriceChart.tsx
    - frontend/src/components/history/PriceTable.tsx
    - frontend/src/components/history/TimeRangeFilter.tsx
    - frontend/src/__tests__/PriceChart.test.tsx
    - frontend/src/__tests__/PriceTable.test.tsx
    - frontend/src/__tests__/PriceHistoryView.test.tsx
  modified:
    - frontend/src/types/api.ts
    - frontend/src/lib/api.ts
    - frontend/src/lib/format.ts
    - frontend/src/hooks/use-watch-queries.ts
    - frontend/src/components/query/QuerySheet.tsx
    - frontend/src/components/query/ListingRow.tsx
    - frontend/package.json

key-decisions:
  - "onViewHistory prop made optional (?) on ListingRow to maintain backward compatibility with existing test renders"
  - "Chart data sorted oldest-first for proper line rendering, API returns newest-first"
  - "thresholdDollars=null when thresholdCents is 0 to suppress reference line"

patterns-established:
  - "Slide-over content swapping: QuerySheet selectedListingId state toggles between listing list and detail view"
  - "Client-side time range filtering: fetch all history once, filter with filterByRange utility"

requirements-completed: [HIST-03, HIST-04, HIST-05]

# Metrics
duration: 4min
completed: 2026-03-20
---

# Phase 6 Plan 01: Price History Visualization Summary

**Recharts line chart with threshold overlay, sortable price table, and time range filtering wired into QuerySheet slide-over via View history links**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T19:29:50Z
- **Completed:** 2026-03-20T19:33:38Z
- **Tasks:** 3
- **Files modified:** 14

## Accomplishments
- Interactive line chart with dashed threshold reference line (HIST-03)
- Sortable table with date/price/delta columns, newest-first default sort (HIST-04)
- Client-side time range filtering (7d/30d/90d/all) applied to both chart and table (HIST-05)
- Full data layer: HistoryRecord type, API method, useListingHistory hook, format utilities
- Loading skeleton, error state with retry, and empty state handling
- 13 new tests passing across PriceChart, PriceTable, and PriceHistoryView

## Task Commits

Each task was committed atomically:

1. **Task 1: Install Recharts and add data layer** - `c59402b` (feat)
2. **Task 2: Build history components and tests** - `d27a09e` (feat)
3. **Task 3: Wire history view into QuerySheet** - `36d08bc` (feat)

## Files Created/Modified
- `frontend/src/components/history/PriceHistoryView.tsx` - Container with back button, header, filter, chart, table, and loading/error/empty states
- `frontend/src/components/history/PriceChart.tsx` - Recharts LineChart with threshold ReferenceLine
- `frontend/src/components/history/PriceTable.tsx` - Sortable table with date/price/delta columns
- `frontend/src/components/history/TimeRangeFilter.tsx` - Segmented 7d/30d/90d/all buttons + filterByRange utility
- `frontend/src/types/api.ts` - Added HistoryRecord interface
- `frontend/src/lib/api.ts` - Added retailerUrls.history() method
- `frontend/src/lib/format.ts` - Added formatDate and formatChartDate
- `frontend/src/hooks/use-watch-queries.ts` - Added listingHistory query key and useListingHistory hook
- `frontend/src/components/query/QuerySheet.tsx` - Added selectedListingId state, PriceHistoryView conditional rendering
- `frontend/src/components/query/ListingRow.tsx` - Added onViewHistory callback prop
- `frontend/src/__tests__/PriceChart.test.tsx` - Chart rendering and threshold line tests
- `frontend/src/__tests__/PriceTable.test.tsx` - Table rendering, sort, and delta color tests
- `frontend/src/__tests__/PriceHistoryView.test.tsx` - Loading/error/empty/data state tests

## Decisions Made
- Made onViewHistory optional on ListingRow props to maintain backward compatibility with existing test renders that don't pass it
- Chart data is reverse-sorted (oldest first) before rendering for proper line chart chronology
- thresholdDollars passed as null when thresholdCents is 0 to suppress the reference line

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Two pre-existing test failures found in QuerySheet.test.tsx and StatusDot.test.tsx (stale class name assertions). These are not caused by this plan's changes and are logged in deferred-items.md.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- History visualization complete, ready for dark mode toggle and polish (Plan 02)
- All four history components exported and wired into QuerySheet

---
*Phase: 06-price-history-visualization-polish*
*Completed: 2026-03-20*
