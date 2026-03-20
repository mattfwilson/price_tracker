---
phase: 05-dashboard-frontend
plan: 01
subsystem: ui
tags: [react, vite, typescript, shadcn-ui, tanstack-query, tailwind-v4, vitest]

# Dependency graph
requires:
  - phase: 04-scheduling-alerts
    provides: "Backend API endpoints for watch queries, alerts, SSE streaming"
provides:
  - "React + Vite + TypeScript frontend scaffold with 15 shadcn/ui components"
  - "TypeScript interfaces mirroring all backend Pydantic schemas"
  - "Typed API client covering all 11 backend endpoints"
  - "TanStack Query hooks for all CRUD operations with cache invalidation"
  - "Format utilities (price, delta icon, relative time)"
  - "Layout shell with Header and two routes"
  - "Vitest test infrastructure with jsdom"
affects: [05-02, 05-03, 05-04]

# Tech tracking
tech-stack:
  added: [react-19, vite-8, typescript-5.9, tailwindcss-v4, shadcn-ui, tanstack-react-query, react-router-dom, zod, sonner, lucide-react, vitest, testing-library]
  patterns: [typed-fetch-wrapper, tanstack-query-hooks-with-invalidation, path-aliases-via-vite-resolve]

key-files:
  created:
    - frontend/src/types/api.ts
    - frontend/src/lib/api.ts
    - frontend/src/lib/format.ts
    - frontend/src/hooks/use-watch-queries.ts
    - frontend/src/hooks/use-alerts.ts
    - frontend/src/components/layout/Layout.tsx
    - frontend/src/components/layout/Header.tsx
    - frontend/src/components/shared/EmptyState.tsx
    - frontend/src/components/shared/ErrorState.tsx
    - frontend/src/pages/DashboardPage.tsx
    - frontend/src/pages/AlertsPage.tsx
    - frontend/vitest.config.ts
  modified:
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/src/index.css
    - frontend/vite.config.ts
    - frontend/tsconfig.app.json

key-decisions:
  - "Manual Vite scaffold + shadcn init (CLI interactive mode incompatible with automation)"
  - "Fixed shadcn sonner component to remove next-themes dependency and circular self-import"
  - "Pause/resume uses PATCH /watch-queries/{id} with is_active body (not separate endpoints)"
  - "Google Fonts @import placed before @import tailwindcss to satisfy CSS @import ordering rule"

patterns-established:
  - "Typed API client: all fetch calls through apiFetch<T> with ApiError handling"
  - "TanStack Query hooks: one hook per operation with automatic cache invalidation on mutations"
  - "Query keys centralized in queryKeys object shared across hook files"
  - "Formatting utils: cents-to-dollars via formatPrice, direction-to-arrow via deltaIcon"

requirements-completed: [DASH-01]

# Metrics
duration: 6min
completed: 2026-03-19
---

# Phase 5 Plan 01: Frontend Foundation Summary

**React 19 + Vite 8 + shadcn/ui scaffold with typed API client, TanStack Query hooks for all CRUD operations, and Vitest test infrastructure**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-20T03:42:00Z
- **Completed:** 2026-03-20T03:48:07Z
- **Tasks:** 2
- **Files modified:** 43

## Accomplishments
- Fully bootable React app on localhost:5173 with Tailwind v4, shadcn zinc theme, DM Sans + Outfit fonts
- 15 shadcn/ui components installed (card, dialog, alert-dialog, dropdown-menu, button, input, label, select, badge, table, popover, skeleton, sonner, sheet, separator)
- Complete TypeScript type layer mirroring all backend Pydantic schemas
- API client covering all 11 endpoints with typed responses and error handling
- 10 TanStack Query hooks with proper cache invalidation for all watch query and alert operations
- Two routes (/ and /alerts) with layout shell, sticky header, and stub pages

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold React + Vite + shadcn/ui project** - `fd62f61` (feat)
2. **Task 2: Create types, API client, format utils, hooks** - `4d0e0fc` (feat)

**Supporting:** `9f457e5` (chore: frontend .gitignore)

## Files Created/Modified
- `frontend/src/types/api.ts` - TypeScript interfaces for all API responses
- `frontend/src/lib/api.ts` - Typed fetch wrapper and API client object
- `frontend/src/lib/format.ts` - formatPrice, deltaIcon, formatRelativeTime utilities
- `frontend/src/hooks/use-watch-queries.ts` - TanStack Query hooks for watch query CRUD + pause/resume/scrape
- `frontend/src/hooks/use-alerts.ts` - TanStack Query hooks for alerts with 30s polling
- `frontend/src/components/layout/Layout.tsx` - App shell with Header and Outlet
- `frontend/src/components/layout/Header.tsx` - Sticky header with "Price Scraper" branding
- `frontend/src/components/shared/EmptyState.tsx` - Reusable empty state with optional CTA
- `frontend/src/components/shared/ErrorState.tsx` - Error display with destructive icon
- `frontend/src/main.tsx` - QueryClientProvider + BrowserRouter + Toaster providers
- `frontend/src/App.tsx` - React Router with / and /alerts routes
- `frontend/vitest.config.ts` - Vitest with jsdom environment and path aliases

## Decisions Made
- Used manual Vite scaffold + shadcn CLI (non-interactive `shadcn init -t vite` prompted for input; manual approach more reliable)
- Pause/resume implemented via PATCH /watch-queries/{id} with `{ is_active: false/true }` body, matching actual backend implementation (no separate pause/resume endpoints)
- Google Fonts @import placed before Tailwind @import to satisfy CSS spec ordering requirements
- ApiError uses explicit field assignment instead of TypeScript parameter properties (erasableSyntaxOnly flag in tsconfig)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed shadcn sonner component circular import and next-themes dependency**
- **Found during:** Task 1 (Project scaffold)
- **Issue:** shadcn-generated sonner.tsx imported from itself (`@/components/ui/sonner`) and used `next-themes` (not installed/not Next.js)
- **Fix:** Rewrote to import `Toaster` and `ToasterProps` directly from `sonner` package, removed next-themes usage
- **Files modified:** frontend/src/components/ui/sonner.tsx
- **Verification:** npm run build passes cleanly
- **Committed in:** fd62f61 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed CSS @import ordering warning**
- **Found during:** Task 1 (Build verification)
- **Issue:** Google Fonts @import url() placed after @import "tailwindcss" which expands to rules, violating CSS spec
- **Fix:** Moved Google Fonts @import before Tailwind @import
- **Files modified:** frontend/src/index.css
- **Verification:** Build produces zero warnings
- **Committed in:** fd62f61 (Task 1 commit)

**3. [Rule 1 - Bug] Fixed ApiError class parameter properties with erasableSyntaxOnly**
- **Found during:** Task 2 (TypeScript compilation)
- **Issue:** TypeScript `erasableSyntaxOnly` flag disallows `public` parameter properties in constructors
- **Fix:** Changed to explicit field declarations with constructor assignment
- **Files modified:** frontend/src/lib/api.ts
- **Verification:** tsc --noEmit and npm run build both pass
- **Committed in:** 4d0e0fc (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3 bugs)
**Impact on plan:** All fixes necessary for build correctness. No scope creep.

## Issues Encountered
- shadcn CLI `init -t vite` command entered interactive mode despite flags; resolved by manual project setup
- shadcn `add` command created files in literal `@/` directory instead of `src/`; resolved by copying files to correct location and updating components.json aliases

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All foundation infrastructure ready for Plan 02 (dashboard card grid, QueryCard component)
- Types, hooks, API client, and layout shell are in place for all subsequent plans
- Vitest configured and ready for component tests

## Self-Check: PASSED

All 10 key files verified present. All 3 commits verified in git log.

---
*Phase: 05-dashboard-frontend*
*Completed: 2026-03-19*
