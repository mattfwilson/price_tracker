---
phase: 08-scrape-health-dashboard
plan: "03"
subsystem: frontend
tags: [health-dashboard, query-card, mini-dots, react, tdd, tanstack-query]
dependency_graph:
  requires:
    - "Phase 08-01: UrlHealthResponse type and /scrape-health/urls endpoint"
    - "Phase 08-02: useHealthUrls hook, HealthStatusDot component"
    - "Phase 05: QueryCard, DashboardPage, QueryCardGrid"
  provides:
    - "UrlHealthDots component rendering per-URL health mini-dots"
    - "QueryCard with healthData prop showing per-URL health status"
    - "DashboardPage single-fetch pattern via useHealthUrls + healthByQuery map"
    - "QueryCardGrid healthByQuery prop threading"
  affects:
    - "frontend/src/components/dashboard/QueryCard.tsx: healthData prop added"
    - "frontend/src/components/dashboard/QueryCardGrid.tsx: healthByQuery prop threading"
    - "frontend/src/pages/DashboardPage.tsx: useHealthUrls() single fetch + useMemo map"
tech_stack:
  added:
    - "UrlHealthDots: mini-dot row component using HealthStatusDot size=sm with title tooltip"
    - "healthByQuery: useMemo-computed Record<number, UrlHealthResponse[]> for O(1) card lookup"
  patterns:
    - "TDD: RED tests committed before implementation, GREEN verified with 9 passing tests"
    - "Single-fetch pattern: useHealthUrls() once at DashboardPage, filtered via healthByQuery map"
    - "Prop threading: DashboardPage -> QueryCardGrid -> QueryCard (no N+1 per RESEARCH.md Pitfall 3)"
key_files:
  created:
    - frontend/src/components/dashboard/UrlHealthDots.tsx
    - frontend/src/__tests__/UrlHealthDots.test.tsx
  modified:
    - frontend/src/components/dashboard/QueryCard.tsx
    - frontend/src/components/dashboard/QueryCardGrid.tsx
    - frontend/src/pages/DashboardPage.tsx
decisions:
  - "Threaded healthData through QueryCardGrid (not direct QueryCard rendering) to preserve existing grid abstraction"
  - "title attribute used for tooltip (per UI-SPEC D-14: simplicity over shadcn Tooltip)"
  - "useMemo for healthByQuery map to avoid recomputation on every render"
metrics:
  duration: "3min"
  completed: "2026-03-23"
  tasks_completed: 1
  files_created: 2
  files_modified: 3
---

# Phase 08 Plan 03: QueryCard Health Mini-Dots Summary

UrlHealthDots component renders per-URL health mini-dots in QueryCard below StatusDot line, with health data fetched once at DashboardPage level via useHealthUrls() and distributed through QueryCardGrid to each card — no N+1 requests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for UrlHealthDots | 427427c | __tests__/UrlHealthDots.test.tsx |
| 1 (GREEN) | UrlHealthDots, QueryCard prop, DashboardPage single-fetch | d3f2d82 | UrlHealthDots.tsx, QueryCard.tsx, QueryCardGrid.tsx, DashboardPage.tsx |

## What Was Built

1. **UrlHealthDots component** (`frontend/src/components/dashboard/UrlHealthDots.tsx`) - Renders a vertical list of per-URL health dot rows. Each row uses `HealthStatusDot` with `size="sm"` for `h-2 w-2` dots plus a domain label in `text-xs text-muted-foreground`. Each row has a `title` attribute with format `"{domain} · {success}/{window} · last success {relative_time}"`. Returns null when health data is empty or undefined.

2. **QueryCard modifications** - Added optional `healthData?: UrlHealthResponse[]` prop. Added `UrlHealthDots` import. Renders `<UrlHealthDots healthData={healthData} />` after the StatusDot line and before the schedule line. `StatusDot` is preserved unmodified (per D-15).

3. **QueryCardGrid modifications** - Added optional `healthByQuery?: Record<number, UrlHealthResponse[]>` prop. Passes `healthData={healthByQuery?.[query.id]}` to each `QueryCard` in the render loop.

4. **DashboardPage modifications** - Added `useHealthUrls()` hook call to fetch all URL health data once. Added `useMemo` to build `healthByQuery` lookup map indexed by `watch_query_id`. Passes `healthByQuery={healthByQuery}` to `QueryCardGrid`. One GET /scrape-health/urls request serves all cards (no N+1).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Architecture] Health data threaded through QueryCardGrid**
- **Found during:** Task 1 implementation
- **Issue:** DashboardPage renders QueryCards via QueryCardGrid abstraction, not directly. The plan's acceptance criterion expected `healthData={healthByQuery[` in DashboardPage JSX, but direct QueryCard rendering is not how DashboardPage works.
- **Fix:** Extended QueryCardGrid to accept `healthByQuery` prop and pass `healthData={healthByQuery?.[query.id]}` to each QueryCard. DashboardPage passes `healthByQuery` to QueryCardGrid.
- **Files modified:** QueryCardGrid.tsx (added prop threading)
- **Commit:** d3f2d82

## Known Stubs

None - UrlHealthDots renders real data from the `useHealthUrls()` hook. When no health data is available (loading or no attempts recorded), the component renders nothing rather than a placeholder.

## Pre-existing Test Failures (Deferred)

3 pre-existing failures unrelated to Plan 03 work (same as Plans 01 and 02):
- `src/__tests__/StatusDot.test.tsx`: 1 failure (bg-zinc-400 vs bg-zinc-500 class mismatch)
- `src/__tests__/QuerySheet.test.tsx`: 2 failures (delta color class + title attribute assertion)

These were present before this plan and are already logged in the deferred items.

## Self-Check: PASSED

Files created:
- frontend/src/components/dashboard/UrlHealthDots.tsx: FOUND
- frontend/src/__tests__/UrlHealthDots.test.tsx: FOUND

Files modified:
- frontend/src/components/dashboard/QueryCard.tsx: FOUND (contains UrlHealthDots, healthData prop)
- frontend/src/components/dashboard/QueryCardGrid.tsx: FOUND (contains healthByQuery prop)
- frontend/src/pages/DashboardPage.tsx: FOUND (contains useHealthUrls, healthByQuery)

Commits:
- 427427c: test(08-03): add failing tests for UrlHealthDots component - FOUND
- d3f2d82: feat(08-03): UrlHealthDots component, QueryCard prop threading, and DashboardPage single-fetch - FOUND
