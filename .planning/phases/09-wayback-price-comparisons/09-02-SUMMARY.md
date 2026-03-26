---
phase: 09-wayback-price-comparisons
plan: "02"
subsystem: ui
tags: [react, typescript, tailwind, shadcn, wayback, price-history, badge]

# Dependency graph
requires:
  - phase: 09-01
    provides: backend wayback fields in RetailerUrlWithLatest API response
provides:
  - WaybackStats inline component rendering 30d/90d prices, rolling averages, and all-time extremes per listing
  - DealBadge inline component showing green "Good deal" / red "Above avg" based on 90-day average comparison
  - formatShortDate utility alias for "Mar 12" date format in wayback context
  - Extended RetailerUrlWithLatest TypeScript interface with 10 wayback fields
affects: [frontend, ListingRow, query detail slide-over]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Inline helper components (DealBadge, WaybackStats) defined above main export function for colocation
    - Graceful omission pattern: null-check each field before rendering, return null when no data
    - Minimum floor suppression: avg and DealBadge hidden when count < 3 data points

key-files:
  created: []
  modified:
    - frontend/src/types/api.ts
    - frontend/src/lib/format.ts
    - frontend/src/components/query/ListingRow.tsx

key-decisions:
  - "formatShortDate added as alias for existing formatChartDate (same month/day logic) rather than duplicating implementation"
  - "WaybackStats and DealBadge defined as inline functions in ListingRow.tsx (not extracted to separate files) for colocation with their only consumer"
  - "DealBadge suppressed entirely when avg_90d_count < 3, matching D-05 threshold rule"

patterns-established:
  - "Wayback stats row: mt-1 flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground"
  - "Deal badge colors: emerald-500/15 bg / emerald-400 text / emerald-500/30 border for good, red-500/15 / red-400 / red-500/30 for above avg"

requirements-completed: [WAYBACK-01, WAYBACK-02, WAYBACK-03, WAYBACK-04]

# Metrics
duration: ~5min
completed: "2026-03-25"
---

# Phase 9 Plan 02: Wayback Price Comparisons Frontend Summary

**WaybackStats and DealBadge components wired into ListingRow, displaying 30d/90d prices with dates, rolling averages with point counts, good-deal/above-avg badges, and all-time high/low per listing**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-25
- **Completed:** 2026-03-25
- **Tasks:** 1 of 2 completed (Task 2 is a human-verify checkpoint)
- **Files modified:** 3

## Accomplishments
- Extended `RetailerUrlWithLatest` TypeScript interface with 10 optional wayback fields matching backend schema
- Added `formatShortDate` as alias for `formatChartDate` in `format.ts` for wayback context clarity
- Added `DealBadge` inline component: green "Good deal" when current price < 90d average, red "Above avg" otherwise, suppressed when avg_90d_count < 3
- Added `WaybackStats` inline component: renders compact stats row with 30d/90d prices (with dates), 90d rolling average (when >= 3 pts), DealBadge, and all-time low/high sub-row
- TypeScript compiles cleanly with no errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add wayback fields to TypeScript types, formatShortDate, and WaybackStats/DealBadge in ListingRow** - `b7d3a1c` (feat)
2. **Task 2: Verify wayback stats display in browser** - Awaiting human verification (checkpoint)

## Files Created/Modified
- `frontend/src/types/api.ts` - Extended RetailerUrlWithLatest with 10 optional wayback fields
- `frontend/src/lib/format.ts` - Added formatShortDate alias for formatChartDate
- `frontend/src/components/query/ListingRow.tsx` - Added DealBadge and WaybackStats inline components, wired <WaybackStats url={url} /> into the listing layout

## Decisions Made
- `formatShortDate` added as `export const formatShortDate = formatChartDate` -- avoids duplicating implementation since logic is identical
- `WaybackStats` and `DealBadge` defined inline in `ListingRow.tsx` rather than extracted to separate files -- only used in this component
- Deal badge suppression threshold matches D-05: hidden when `avg_90d_count < 3`
- Both WaybackStats rows (`div` for segments + `div` for all-time extremes) use `mt-1` top margin to match the existing price/delta line spacing

## Deviations from Plan

None - Task 1 was already implemented and committed prior to this execution session. Plan executed exactly as specified.

## Issues Encountered

None. TypeScript compiled cleanly after implementation. No runtime errors encountered.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Frontend wayback display complete pending human visual verification (Task 2 checkpoint)
- Once verified, Phase 09 wayback-price-comparisons is complete
- Ready for Phase 10: fuzzy product matching

## Known Stubs

None. All wayback data flows from real backend computation or is gracefully omitted when null. No placeholders or hardcoded values.

## Self-Check: PASSED
- `frontend/src/types/api.ts` exists and contains `price_30d_cents: number | null` ✓
- `frontend/src/lib/format.ts` exists and contains `formatShortDate` ✓
- `frontend/src/components/query/ListingRow.tsx` exists and contains `WaybackStats`, `DealBadge`, `Good deal`, `Above avg`, `Low:`, `High:` ✓
- Commit `b7d3a1c` exists in git log ✓
- `npx tsc --noEmit` exits 0 ✓

---
*Phase: 09-wayback-price-comparisons*
*Completed: 2026-03-25*
