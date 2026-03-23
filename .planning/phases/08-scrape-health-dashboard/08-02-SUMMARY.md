---
phase: 08-scrape-health-dashboard
plan: "02"
subsystem: frontend
tags: [health-dashboard, react, tanstack-query, shadcn, tdd]
dependency_graph:
  requires:
    - "Phase 08-01: GET /scrape-health/urls and /scrape-health/query/{id} endpoints"
    - "Phase 05: TanStack Query setup, existing api.ts/types/api.ts patterns"
    - "Phase 06: shadcn Table, Header, App.tsx routing"
  provides:
    - "HealthPage at /health route"
    - "HealthTable sortable by status/query/lastSuccess"
    - "HealthStatusDot (healthy=emerald, degraded=amber, failing=red)"
    - "HealthFilter All/Degraded&Failing toggle"
    - "useHealthUrls and useHealthByQuery hooks"
    - "scrapeHealth API client methods"
    - "Health nav link in Header"
  affects:
    - "frontend/src/App.tsx: /health route added"
    - "frontend/src/components/layout/Header.tsx: Health NavLink added"
    - "Plans 03: QueryCard mini-dots can use useHealthByQuery hook"
tech_stack:
  added:
    - "HealthStatusDot: reusable dot component with healthy/degraded/failing semantic colors"
    - "HealthTable: STATUS_ORDER map with failing=2/degraded=1/healthy=0 for desc-sort failing-first"
    - "useHealthUrls/useHealthByQuery: TanStack Query hooks with select transform"
  patterns:
    - "TDD: RED tests committed before implementation, GREEN verified with 10 passing tests"
    - "Follows AlertsPage pattern: SkeletonRows, EmptyState, ErrorState"
    - "NavLink with isActive callback for active nav state"
key_files:
  created:
    - frontend/src/hooks/use-health.ts
    - frontend/src/components/health/HealthStatusDot.tsx
    - frontend/src/components/health/HealthFilter.tsx
    - frontend/src/components/health/HealthTable.tsx
    - frontend/src/pages/HealthPage.tsx
    - frontend/src/__tests__/HealthTable.test.tsx
  modified:
    - frontend/src/types/api.ts
    - frontend/src/lib/api.ts
    - frontend/src/components/layout/Header.tsx
    - frontend/src/App.tsx
decisions:
  - "STATUS_ORDER uses failing=2/degraded=1/healthy=0 (higher=worse) so desc sort correctly puts failing first"
  - "Default sort direction for status column is desc so worst URLs appear at top by default"
  - "Nulls-last for lastSuccess sort implemented in sort comparator (always return 1 if a is null, -1 if b is null)"
metrics:
  duration: "3min"
  completed: "2026-03-23"
  tasks_completed: 2
  files_created: 6
  files_modified: 4
---

# Phase 08 Plan 02: Health Frontend Summary

HealthPage at /health with sortable/filterable HealthTable, HealthStatusDot (emerald/amber/red), HealthFilter toggle, useHealthUrls TanStack Query hook, scrapeHealth API client, Header nav link, and routing — all implemented TDD with 10 passing tests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | TypeScript types, API client, TanStack Query hook | ec767d2 | types/api.ts, lib/api.ts, hooks/use-health.ts |
| 2 (RED) | Failing tests for health components | d703c0c | __tests__/HealthTable.test.tsx |
| 2 (GREEN) | Health page components, routing, nav link | 9bfa290 | HealthStatusDot, HealthFilter, HealthTable, HealthPage, Header, App |

## What Was Built

1. **TypeScript types** - `HealthStatus` union type and `UrlHealthResponse`/`HealthListResponse` interfaces added to `types/api.ts`, matching the backend Pydantic schemas from Plan 01.

2. **API client** - `api.scrapeHealth.urls()` and `api.scrapeHealth.byQuery(id)` added to `lib/api.ts`, consuming the `/scrape-health/urls` and `/scrape-health/query/{id}` endpoints.

3. **TanStack Query hooks** - `useHealthUrls()` and `useHealthByQuery(watchQueryId)` in `hooks/use-health.ts`. Both use `select: (data) => data.urls` to unwrap the `urls` array directly.

4. **HealthStatusDot** - Reusable dot component mapping `healthy` → `bg-emerald-500`, `degraded` → `bg-amber-500`, `failing` → `bg-red-500`. Supports `showLabel` and `size` props.

5. **HealthFilter** - Toggle buttons (All / Degraded & Failing) using shadcn `Button` with `variant="default"` for active state and `variant="outline"` for inactive.

6. **HealthTable** - Sortable table using shadcn `Table` components. Three sortable columns: Status (failing-first by default via `STATUS_ORDER`), Watch Query (alphabetical), Last Success (nulls always last regardless of direction). ArrowUp/ArrowDown icons on active column header.

7. **HealthPage** - Full page at `/health` with loading skeleton (5 rows), empty state, error state, and filter-aware table rendering. Follows AlertsPage pattern.

8. **Header nav link** - React Router `NavLink` to `/health` with `isActive` callback for `text-foreground` active / `text-muted-foreground` inactive styling.

9. **App routing** - `/health` route added inside Layout route in `App.tsx`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] STATUS_ORDER direction mismatch**
- **Found during:** Task 2 GREEN phase (test failure)
- **Issue:** Plan specified `direction: "desc"` as default with `failing=0 > degraded=1 > healthy=2`. With `(aOrder - bOrder) * -1`, failing (0) vs healthy (2) gives `(0-2)*-1 = 2 > 0` which puts failing LAST, not first.
- **Fix:** Changed `STATUS_ORDER` to `failing=2, degraded=1, healthy=0` so desc direction puts the highest-valued (worst) status first.
- **Files modified:** frontend/src/components/health/HealthTable.tsx
- **Commit:** 9bfa290 (inline fix before commit)

## Known Stubs

None - HealthTable renders real data from the `/scrape-health/urls` endpoint. The `useHealthUrls` hook is wired to a real API call (not mocked data). Loading/empty/error states are all properly handled.

## Pre-existing Test Failures (Deferred)

3 pre-existing test failures unrelated to Plan 02 work (same as Plan 01):
- `src/__tests__/QuerySheet.test.tsx`: 2 failures (delta color class assertion)
- `src/__tests__/StatusDot.test.tsx`: 1 failure (bg-zinc-400 vs bg-zinc-500 class mismatch)

These were present before this plan and are already logged in Phase 07's deferred items.

## Self-Check: PASSED

Files created:
- frontend/src/hooks/use-health.ts: FOUND
- frontend/src/components/health/HealthStatusDot.tsx: FOUND
- frontend/src/components/health/HealthFilter.tsx: FOUND
- frontend/src/components/health/HealthTable.tsx: FOUND
- frontend/src/pages/HealthPage.tsx: FOUND
- frontend/src/__tests__/HealthTable.test.tsx: FOUND

Commits:
- ec767d2: feat(08-02): health types, API client methods, and TanStack Query hook - FOUND
- d703c0c: test(08-02): add failing tests for HealthTable, HealthFilter, HealthStatusDot - FOUND
- 9bfa290: feat(08-02): health page components, routing, and nav link - FOUND
