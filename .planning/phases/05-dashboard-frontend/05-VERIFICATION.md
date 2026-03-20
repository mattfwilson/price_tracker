---
phase: 05-dashboard-frontend
verified: 2026-03-20T00:20:00Z
status: human_needed
score: 12/13 must-haves verified
re_verification: false
human_verification:
  - test: "Open dashboard at localhost:5173, start backend, observe bell icon with real alerts"
    expected: "Unread count badge appears on bell icon; clicking bell opens popover with alert rows and unread blue dots"
    why_human: "SSE connection and real-time badge update require a live backend and cannot be verified programmatically"
  - test: "Trigger a scrape that causes a price drop below threshold; observe toast"
    expected: "Sonner toast appears bottom-right with format '{query_name} — $X.XX at {retailer_name}' and description 'Below threshold!'"
    why_human: "SSE event delivery and toast rendering require a live connection"
  - test: "Navigate to /alerts with real data"
    expected: "Table renders all columns (Status, Query Name, Product, Price, Retailer, Time); clicking a row marks it read (blue dot disappears)"
    why_human: "Real data needed to observe the full table rendering and optimistic mark-as-read behavior"
  - test: "Open a QuerySheet slide-over by clicking a card with real scrape data"
    expected: "Sheet opens at 480px width; all matching listings appear with prices, delta arrows, and the lowest-price listing shows 'Lowest' badge"
    why_human: "Requires real scrape data in DB; lowest-badge logic depends on actual price values"
---

# Phase 5: Dashboard Frontend Verification Report

**Phase Goal:** Build a React + TypeScript dashboard frontend that lets users view watch queries, see current prices with threshold alerts, manage (create/edit/delete) watch queries, and receive real-time alert notifications.
**Verified:** 2026-03-20T00:20:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | React app boots with QueryClientProvider + BrowserRouter | VERIFIED | `frontend/src/main.tsx` wraps App with both providers; build exits 0 |
| 2 | Two routes exist: / renders DashboardPage, /alerts renders AlertsPage | VERIFIED | `App.tsx` lines 10-11: `path="/"` and `path="/alerts"` inside Layout route |
| 3 | API client covers all 11 backend endpoints | VERIFIED | `api.ts` has watchQueries.{list,detail,create,update,delete,pause,resume,scrape} and alerts.{list,unreadCount,markRead,dismissAll} |
| 4 | TypeScript types mirror backend Pydantic schemas exactly | VERIFIED | `api.ts` exports all 11 interfaces; `direction: "new" \| "higher" \| "lower" \| "unchanged"` matches backend literal |
| 5 | TanStack Query hooks exist for all CRUD and alert operations | VERIFIED | `use-watch-queries.ts` exports 8 hooks; `use-alerts.ts` exports 4 hooks with correct cache invalidation |
| 6 | Dashboard displays watch queries as responsive card grid | VERIFIED | `QueryCardGrid.tsx` renders `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`; skeleton, empty, and error states all present |
| 7 | Cards show lowest price, threshold breach highlighting, and status dot | VERIFIED | `QueryCard.tsx` calls `useWatchQueryDetail`, computes `lowestPrice`, applies `border-l-emerald-500` + "Below threshold" badge when `lowestPrice <= threshold_cents` |
| 8 | Three-dot card menu has Edit/Pause-Resume/Scrape Now/Delete with stopPropagation | VERIFIED | `CardMenu.tsx` line 38: `onClick={(e) => e.stopPropagation()}` on trigger; all four actions wired |
| 9 | User can drill down into a watch query via QuerySheet slide-over | VERIFIED | `QuerySheet.tsx` uses Sheet side="right" at `sm:w-[480px]`; calls `useWatchQueryDetail`; `findLowestPriceUrlId` assigns "Lowest" badge |
| 10 | User can create/edit/delete watch queries via dialogs | VERIFIED | `QueryFormDialog.tsx` handles both modes; `DeleteQueryDialog.tsx` uses AlertDialog with "Keep Query"/"Delete" buttons; all wired in DashboardPage |
| 11 | Form converts dollar input to cents before API submission | VERIFIED | `QueryFormDialog.tsx` line 123: `Math.round(parseFloat(threshold) * 100)` |
| 12 | Bell dropdown shows unread count and recent alerts | VERIFIED | `BellDropdown.tsx` uses `useUnreadCount` and `useAlerts(10)`; badge renders when `unreadCount > 0` |
| 13 | SSE connection receives alert events and shows toasts with cache update | HUMAN_NEEDED | `use-sse.ts` wiring verified in code: `EventSource`, `addEventListener("alert", ...)`, `setQueryData`, `invalidateQueries`, `toast(...)`. Real delivery requires live backend |

**Score:** 12/13 truths verified (13th requires human with live backend)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/types/api.ts` | TypeScript interfaces for all API responses | VERIFIED | 11 interfaces; all backend schemas mirrored exactly |
| `frontend/src/lib/api.ts` | Typed fetch wrapper and API client | VERIFIED | `ApiError` class; `api.watchQueries` and `api.alerts` namespaces; all 11 endpoints |
| `frontend/src/lib/format.ts` | Price formatting and delta icon utilities | VERIFIED | `formatPrice`, `deltaIcon`, `formatRelativeTime` all exported and substantive |
| `frontend/src/hooks/use-watch-queries.ts` | TanStack Query hooks for watch query CRUD | VERIFIED | 8 exported hooks; `queryKeys` object; all mutations invalidate correct keys |
| `frontend/src/hooks/use-alerts.ts` | TanStack Query hooks for alert operations | VERIFIED | 4 hooks; `useUnreadCount` has `refetchInterval: 30_000` |
| `frontend/src/hooks/use-sse.ts` | SSE hook pushing alerts into query cache | VERIFIED | `EventSource` to `/alerts/stream`; named "alert" event listener; `setQueryData`, `invalidateQueries`, toast, 3s auto-reconnect |
| `frontend/src/components/layout/Layout.tsx` | App shell calling useAlertSSE | VERIFIED | Line 6: `useAlertSSE()` called at top of Layout; renders Header + Outlet |
| `frontend/src/components/layout/Header.tsx` | Sticky header with BellDropdown | VERIFIED | Imports and renders `BellDropdown`; sticky top-0 z-50 |
| `frontend/src/pages/DashboardPage.tsx` | Fully wired dashboard page | VERIFIED | QueryCardGrid + QuerySheet + QueryFormDialog (create + edit) + DeleteQueryDialog all rendered with state callbacks |
| `frontend/src/pages/AlertsPage.tsx` | Full alert log table page | VERIFIED | Table with 6 columns; `useAlerts`, `useMarkAlertRead`, `useDismissAllAlerts`; empty state and skeleton rows |
| `frontend/src/components/dashboard/QueryCard.tsx` | Individual watch query card | VERIFIED | `useWatchQueryDetail`; `formatPrice`; `border-l-emerald-500`; "Below threshold" badge; `hover:shadow-md` |
| `frontend/src/components/dashboard/QueryCardGrid.tsx` | Responsive grid with states | VERIFIED | grid-cols responsive; 6 skeleton cards; EmptyState; ErrorState; NewQueryCard |
| `frontend/src/components/dashboard/StatusDot.tsx` | Colored status indicator | VERIFIED | Four states: emerald/red/amber/zinc; `deriveStatus` exported |
| `frontend/src/components/dashboard/CardMenu.tsx` | Three-dot dropdown menu | VERIFIED | stopPropagation; DropdownMenu; Edit/Pause/Resume/Scrape Now/Delete; text-destructive on delete |
| `frontend/src/components/query/QuerySheet.tsx` | Slide-over drill-down panel | VERIFIED | Sheet side="right" sm:w-[480px]; `useWatchQueryDetail`; `findLowestPriceUrlId`; ListingRow with isLowest |
| `frontend/src/components/query/ListingRow.tsx` | Single listing row with price and delta | VERIFIED | "Lowest" badge; `formatPrice`; `deltaIcon`; "Available in next update" title; cursor-not-allowed; text-emerald-600 / text-red-500 |
| `frontend/src/components/query/QueryFormDialog.tsx` | Create/edit modal with validation | VERIFIED | Dialog; "Create Query"/"Save Changes"; Math.round * 100; all four error messages; schedule options; dynamic URL list |
| `frontend/src/components/query/DeleteQueryDialog.tsx` | Delete confirmation dialog | VERIFIED | AlertDialog; "Keep Query"; "This will permanently remove"; `useDeleteWatchQuery` |
| `frontend/src/components/alerts/BellDropdown.tsx` | Bell icon with popover dropdown | VERIFIED | Popover; Bell; bg-destructive badge; bg-blue-500 unread dot; "Dismiss All"; "View All" link to /alerts; `useMarkAlertRead` |
| `frontend/vitest.config.ts` | Test runner configuration | VERIFIED | jsdom environment; globals; setupFiles; path alias |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main.tsx` | `App.tsx` | QueryClientProvider + BrowserRouter | VERIFIED | Lines 19-26 in main.tsx |
| `App.tsx` | `DashboardPage.tsx` | React Router `path="/"` | VERIFIED | Line 10 in App.tsx |
| `use-watch-queries.ts` | `api.ts` | `queryFn: api.watchQueries.list` | VERIFIED | Lines 14-16 in use-watch-queries.ts |
| `DashboardPage.tsx` | `use-watch-queries.ts` | `useWatchQueries()` hook call | VERIFIED | Line 9 in DashboardPage.tsx |
| `QueryCard.tsx` | `use-watch-queries.ts` | `useWatchQueryDetail(query.id)` | VERIFIED | Line 32 in QueryCard.tsx |
| `QueryCard.tsx` | `format.ts` | `formatPrice` call | VERIFIED | Line 119 in QueryCard.tsx |
| `QuerySheet.tsx` | `use-watch-queries.ts` | `useWatchQueryDetail(queryId)` | VERIFIED | Line 36 in QuerySheet.tsx |
| `QueryFormDialog.tsx` | `use-watch-queries.ts` | `useCreateWatchQuery` + `useUpdateWatchQuery` | VERIFIED | Lines 57-58 in QueryFormDialog.tsx |
| `QueryFormDialog.tsx` | `format.ts` | `Math.round(parseFloat(threshold) * 100)` | VERIFIED | Line 123 in QueryFormDialog.tsx |
| `use-sse.ts` | `/alerts/stream` | `new EventSource("http://localhost:8000/alerts/stream")` | VERIFIED | Line 15 in use-sse.ts |
| `use-sse.ts` | `use-watch-queries.ts` | `queryClient.setQueryData(queryKeys.unreadCount, ...)` | VERIFIED | Lines 22-24 in use-sse.ts |
| `BellDropdown.tsx` | `use-alerts.ts` | `useAlerts` and `useUnreadCount` | VERIFIED | Lines 11-14 in BellDropdown.tsx |
| `Layout.tsx` | `use-sse.ts` | `useAlertSSE()` call | VERIFIED | Line 6 in Layout.tsx |
| `Header.tsx` | `BellDropdown.tsx` | Renders `<BellDropdown />` | VERIFIED | Line 8 in Header.tsx |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DASH-01 | 05-01, 05-02, 05-04 | Dashboard displays all active watch queries with name, lowest price, last scrape timestamp, scrape status | SATISFIED | QueryCard: name, lowestPrice via useWatchQueryDetail, latestScrapedAt, StatusDot |
| DASH-02 | 05-02 | Queries with listing at or below threshold are visually highlighted | SATISFIED | QueryCard: `border-l-[3px] border-l-emerald-500` + "Below threshold" badge when `lowestPrice <= threshold_cents` |
| DASH-03 | 05-03, 05-04 | User can drill down to see all matched listings, current prices, price deltas | SATISFIED | QuerySheet: ListingRow shows product_name, formatPrice, deltaIcon, pct_change, "Lowest" badge |
| DASH-04 | 05-02 | Each query card shows scrape status indicator (success/error/running/paused) | SATISFIED | StatusDot: four states emerald/red/amber/zinc; deriveStatus maps is_active + isScrapingLocal to status |
| UI-01 | 05-03 | Within a watch query's results, lowest-price listing is highlighted | SATISFIED | ListingRow: `isLowest` prop shows "Lowest" Badge; `findLowestPriceUrlId` in QuerySheet correctly identifies minimum |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `StatusDot.tsx` | 36-43 | `deriveStatus` never returns "error" — "error" state defined in config but unreachable via normal flow | Info | StatusDot component supports "error" visually but no code path currently sets it. By design per Plan 02 spec: "there is no error field on LatestScrapeResult currently, so default to ok." Not a blocker. |
| `QuerySheet.tsx` | — | Plan 03 spec called for StatusDot in the sheet header; the implementation omits it | Warning | Sheet header shows threshold text but no status indicator. Minor cosmetic deviation. Sheet core functionality (listing drill-down, Lowest badge) is fully present. |

No blockers found.

### Human Verification Required

#### 1. SSE Real-Time Alert Flow

**Test:** Start the backend (`cd backend && uvicorn main:app`), start the frontend (`cd frontend && npm run dev`), trigger a scrape that drops a price below threshold.
**Expected:** Sonner toast appears bottom-right with format "{query_name} — $X.XX at {retailer_name}" / "Below threshold!"; bell badge increments; popover list updates without page refresh.
**Why human:** SSE delivery, toast rendering, and real-time badge update require a live backend connection.

#### 2. Bell Dropdown Live Badge

**Test:** With the backend running and unread alerts in the DB, load the app at localhost:5173.
**Expected:** Bell icon shows a red badge with the unread count number; clicking the bell opens the popover showing alert rows with blue unread dots.
**Why human:** Requires real data in the DB and a running backend for the unread count API call to return a non-zero value.

#### 3. Alert Log Page with Real Data

**Test:** Navigate to /alerts with alerts present in the DB.
**Expected:** Table renders all six columns (Status, Query Name, Product, Price, Retailer, Time); clicking an unread row causes the blue dot to disappear (optimistic mark-as-read via PATCH /alerts/{id}/read); "Dismiss All" clears all rows.
**Why human:** Optimistic UI update on click-to-read requires actual mutation round-trip to observe.

#### 4. QuerySheet Lowest Badge with Real Data

**Test:** Click a watch query card that has multiple retailer URLs with scraped prices.
**Expected:** Sheet opens at 480px; all listing rows render with product name, formatted price, delta arrow + percentage, and the cheapest listing has the "Lowest" badge in emerald.
**Why human:** The lowest-price logic depends on actual price_cents values in scrape results.

### Gaps Summary

No automated-check gaps. All 12 programmatically verifiable must-haves pass:

- Production build exits 0 (vite 8, 1909 modules transformed, 487KB bundle)
- All 37 unit tests pass across 6 test files (QueryCard, QuerySheet, StatusDot, QueryFormDialog, BellDropdown, AlertLogTable)
- All 20 artifact files exist and are substantive (no stubs, no empty implementations)
- All 14 key links are wired end-to-end
- All 5 requirements (DASH-01, DASH-02, DASH-03, DASH-04, UI-01) are satisfied with direct code evidence

The two anti-patterns noted are by-design deviations: (1) `deriveStatus` omitting "error" is explicitly documented in the plan spec as intentional given no error field on the schema, and (2) the missing StatusDot in QuerySheet is a minor cosmetic deviation that does not block any requirement.

The 4 human verification items all require a live backend + database — they cannot be assessed from the static codebase alone.

---

_Verified: 2026-03-20T00:20:00Z_
_Verifier: Claude (gsd-verifier)_
