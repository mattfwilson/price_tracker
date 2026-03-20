---
phase: 06-price-history-visualization-polish
verified: 2026-03-20T15:39:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
human_verification:
  - test: "Visual dark/light toggle"
    expected: "Header Sun/Moon button switches the entire UI between dark terminal palette and light palette. Transition looks correct. Default loads as dark."
    why_human: "Visual rendering and CSS variable application cannot be verified without a browser."
  - test: "Theme persistence across refresh"
    expected: "After toggling to light mode and refreshing the page, app loads in light mode (localStorage key 'price-scraper-theme' read by ThemeProvider)."
    why_human: "localStorage persistence requires a browser session."
  - test: "Price history chart renders with real data"
    expected: "Clicking 'View history' on a listing row with scraped data opens PriceHistoryView inside the slide-over. Chart shows a line with data points and a dashed red threshold line. Back button returns to listing list without closing the slide-over."
    why_human: "Recharts canvas rendering and live API interaction cannot be verified programmatically."
---

# Phase 06: Price History Visualization + Polish Verification Report

**Phase Goal:** Deliver price history visualization and dark/light mode toggle
**Verified:** 2026-03-20T15:39:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Clicking 'View history' on a listing row replaces the slide-over content with a price history view | VERIFIED | `ListingRow` fires `onViewHistory?.(url.id)` on button click; `QuerySheet` has `selectedListingId` state that conditionally renders `PriceHistoryView` vs listing list |
| 2  | Back button returns to listing list without closing the slide-over | VERIFIED | `onBack={() => setSelectedListingId(null)}` in `QuerySheet`; sets state to null, not to close the `Sheet` |
| 3  | Price history line chart renders with data points and a horizontal dashed threshold line | VERIFIED | `PriceChart.tsx` uses Recharts `Line` with `stroke="var(--color-primary)"` and `ReferenceLine` with `strokeDasharray="8 4"` conditionally rendered when `thresholdDollars !== null` |
| 4  | Price history table shows date, price, and delta columns sorted newest-first by default | VERIFIED | `PriceTable.tsx` defaults `sortKey="scraped_at"` and `sortDir="desc"`; `sortRecords` uses date comparison |
| 5  | Clicking table column headers re-sorts the data | VERIFIED | `handleSort` function toggles direction on same key, sets new key with default direction otherwise; test confirms clicking Date header toggles oldest-first/newest-first |
| 6  | Time range filter (7d/30d/90d/all) filters both chart and table simultaneously | VERIFIED | `filterByRange` called before both `chartData` mapping and `PriceTable` render in `PriceHistoryView`; default range `"30d"` confirmed by test |
| 7  | Empty state shows 'No history yet' message when no scrape data exists | VERIFIED | `PriceHistoryView` returns empty state branch when `data.length === 0`; test `shows empty state when no records` passes |
| 8  | Application renders correctly in dark mode (existing palette preserved) | VERIFIED | `.dark { --color-background: oklch(0.11 0.018 264); ... }` in `@layer base` matches original dark palette; `@custom-variant dark (&:where(.dark, .dark *))` declared |
| 9  | Application renders correctly in light mode (new palette) | VERIFIED (automated) / NEEDS HUMAN (visual) | `:root { --color-background: oklch(0.98 0.005 264); ... }` defined with full light palette per UI-SPEC |
| 10 | User can toggle between dark and light mode via a button in the header | VERIFIED | `ThemeToggle` in `Header.tsx` calls `setTheme(theme === "dark" ? "light" : "dark")`; wired next to `BellDropdown` |
| 11 | Theme preference persists across page refresh | VERIFIED (automated) / NEEDS HUMAN (runtime) | `ThemeProvider storageKey="price-scraper-theme"` in `main.tsx`; next-themes handles localStorage read/write |

**Score:** 11/11 truths verified (3 also flagged for human visual confirmation)

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/history/PriceHistoryView.tsx` | Container with back button, header, filter, chart, table | VERIFIED | 122 lines; exports `PriceHistoryView`; contains `useListingHistory`, `filterByRange`, `onBack`, `formatChartDate`, loading/error/empty states |
| `frontend/src/components/history/PriceChart.tsx` | Recharts line chart with threshold ReferenceLine | VERIFIED | 75 lines; exports `PriceChart`; contains `ReferenceLine`, `strokeDasharray="8 4"`, `var(--color-primary)`, `var(--color-destructive)` |
| `frontend/src/components/history/PriceTable.tsx` | Sortable table with date/price/delta | VERIFIED | 142 lines; exports `PriceTable`; contains `sortKey`, `sortDir`, `ArrowUpDown`, `formatPrice`, `formatDate` |
| `frontend/src/components/history/TimeRangeFilter.tsx` | Segmented 7d/30d/90d/all buttons | VERIFIED | 46 lines; exports `TimeRange` type, `filterByRange`, `TimeRangeFilter` |
| `frontend/src/types/api.ts` | HistoryRecord type | VERIFIED | `export interface HistoryRecord` at line 109 with all required fields (id, product_name, price_cents, retailer_name, listing_url, scraped_at, direction, delta_cents, pct_change) |
| `frontend/src/lib/api.ts` | retailerUrls.history() method | VERIFIED | `retailerUrls: { history: (id: number) => apiFetch<HistoryRecord[]>(\`/retailer-urls/${id}/history\`) }` at line 73 |
| `frontend/src/lib/format.ts` | formatDate, formatChartDate | VERIFIED | Both functions exported; `formatDate` with full locale string, `formatChartDate` with short month+day |
| `frontend/src/hooks/use-watch-queries.ts` | useListingHistory hook | VERIFIED | `listingHistory` queryKey and `useListingHistory` hook both present at lines 10 and 94 |
| `frontend/src/__tests__/PriceChart.test.tsx` | 3 chart tests | VERIFIED | 3 tests all pass |
| `frontend/src/__tests__/PriceTable.test.tsx` | 5 table tests | VERIFIED | 5 tests all pass |
| `frontend/src/__tests__/PriceHistoryView.test.tsx` | 5 view tests | VERIFIED | 5 tests all pass |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/layout/ThemeToggle.tsx` | Sun/Moon toggle using next-themes | VERIFIED | Exports `ThemeToggle`; uses `useTheme` from next-themes; `Sun`/`Moon` from lucide-react; `aria-label="Toggle theme"` |
| `frontend/src/index.css` | Light and dark CSS variable definitions in @layer base | VERIFIED | `@custom-variant dark (&:where(.dark, .dark *))` at line 4; `@theme` block contains only font and radius tokens (no `--color-*`); `:root` with light palette and `.dark` with dark palette both in `@layer base` |
| `frontend/src/main.tsx` | ThemeProvider wrapping app | VERIFIED | `import { ThemeProvider } from "next-themes"` and `<ThemeProvider attribute="class" defaultTheme="dark" storageKey="price-scraper-theme">` wrapping app tree |
| `frontend/src/__tests__/ThemeToggle.test.tsx` | 3 toggle tests | VERIFIED | 3 tests all pass |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ListingRow.tsx` | `QuerySheet.tsx` | `onViewHistory` callback prop passes `retailerUrlId` | VERIFIED | `onViewHistory?: (retailerUrlId: number) => void` in interface; `onClick={() => onViewHistory?.(url.id)` in button; `onViewHistory={setSelectedListingId}` passed from QuerySheet |
| `QuerySheet.tsx` | `PriceHistoryView.tsx` | `selectedListingId` state toggles between views | VERIFIED | `useState<number | null>(null)` at line 39; `{selectedListingId && selectedUrl ? <PriceHistoryView ...> : <listing list>}` conditional at line 84 |
| `PriceHistoryView.tsx` | `use-watch-queries.ts` | `useListingHistory` hook fetches from API | VERIFIED | `import { useListingHistory } from "@/hooks/use-watch-queries"` at line 3; `useListingHistory(retailerUrlId)` called at line 31 |
| `use-watch-queries.ts` | `lib/api.ts` | `api.retailerUrls.history()` fetch | VERIFIED | `queryFn: () => api.retailerUrls.history(retailerUrlId!)` at line 97 |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Header.tsx` | `ThemeToggle.tsx` | import and render ThemeToggle | VERIFIED | `import { ThemeToggle } from "./ThemeToggle"` and `<ThemeToggle />` both present |
| `main.tsx` | `next-themes` | ThemeProvider wraps app with attribute='class' | VERIFIED | `<ThemeProvider attribute="class" defaultTheme="dark" storageKey="price-scraper-theme">` at line 21 |
| `index.css` | `next-themes` | `.dark` class selector toggles CSS variables | VERIFIED | `.dark {` selector at line 53 in `@layer base`; ThemeProvider applies `class="dark"` to HTML element via `attribute="class"` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| HIST-03 | 06-01-PLAN.md | Price history displayed as line chart with horizontal dashed threshold line overlay | SATISFIED | `PriceChart.tsx` with `ReferenceLine y={thresholdDollars} strokeDasharray="8 4"`; test verifies line renders and threshold line is conditional |
| HIST-04 | 06-01-PLAN.md | Price history displayed as sortable table with date, price, delta columns (default: newest first) | SATISFIED | `PriceTable.tsx` with `sortKey="scraped_at"` default `sortDir="desc"`; 5 tests verify sorting behavior |
| HIST-05 | 06-01-PLAN.md | User can filter price history chart and table by time range (7d, 30d, 90d, all) | SATISFIED | `TimeRangeFilter` + `filterByRange` applied to both `chartData` and `PriceTable` in `PriceHistoryView`; default `"30d"` confirmed by test |
| UI-02 | 06-02-PLAN.md | Application supports dark mode | SATISFIED | ThemeToggle in header; `@custom-variant dark`; dual `:root`/`.dark` CSS variable selectors; `ThemeProvider` with localStorage persistence |

No orphaned requirements — all 4 IDs declared in plan frontmatter map to verified implementations.

---

## Test Results

| Test File | Tests | Result | Notes |
|-----------|-------|--------|-------|
| `PriceChart.test.tsx` | 3 | PASS | Chart container, threshold line present, threshold line absent |
| `PriceTable.test.tsx` | 5 | PASS | Row count, newest-first default, date sort toggle, price sort, delta color |
| `PriceHistoryView.test.tsx` | 5 | PASS | Loading skeleton, empty state, error state, data render, 30d default |
| `ThemeToggle.test.tsx` | 3 | PASS | Button render, dark-to-light toggle, light-to-dark toggle |
| `QuerySheet.test.tsx` | 2 failing | PRE-EXISTING | Stale class assertions from Phase 05 (`text-emerald-600` vs `text-emerald-400`); documented in `deferred-items.md` |
| `StatusDot.test.tsx` | 1 failing | PRE-EXISTING | Stale class assertion from Phase 05 (`.bg-zinc-400`); documented in `deferred-items.md` |

**Phase 06 tests:** 16/16 pass
**Full suite:** 50/53 pass (3 pre-existing failures from Phase 05, not caused by Phase 06)

---

## TypeScript

`npx tsc --noEmit` exits 0. No type errors.

---

## Anti-Patterns Found

None. No TODO/FIXME/placeholder comments in phase 06 files. No stub implementations. No empty return values.

---

## Human Verification Required

### 1. Dark/Light Mode Visual Appearance

**Test:** Open the app in a browser. Click the Sun/Moon toggle button in the header.
**Expected:** The entire UI switches from the dark terminal palette (near-black background, blue accent) to the light palette (near-white background, blue accent). Typography, cards, borders, and the dot-grid background all update. No FOUC or flash.
**Why human:** CSS variable application and visual rendering require a browser.

### 2. Theme Persistence Across Refresh

**Test:** Toggle to light mode. Reload the page (Cmd+R).
**Expected:** The app loads in light mode. The localStorage key `price-scraper-theme` should be set to `"light"`.
**Why human:** localStorage persistence requires a live browser session.

### 3. Price History View End-to-End

**Test:** Trigger a scrape for a watch query that has at least one retailer URL. After scrape completes, click the query card to open the slide-over. Click "View history" on a listing row.
**Expected:** The slide-over content replaces the listing list with a price history view showing: back button, product name + domain header, time range filter (30d active), a Recharts line chart with a dashed threshold reference line, and a sortable table of scrape records (newest first). Back button returns to the listing list; the slide-over does not close.
**Why human:** Requires live data and Recharts rendering in a browser. The Recharts ResponsiveContainer uses ResizeObserver which does not function in jsdom.

---

## Gaps Summary

None. All automated checks pass. Phase goal is achieved.

---

_Verified: 2026-03-20T15:39:00Z_
_Verifier: Claude (gsd-verifier)_
