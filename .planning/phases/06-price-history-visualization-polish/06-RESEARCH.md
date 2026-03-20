# Phase 6: Price History Visualization + Polish - Research

**Researched:** 2026-03-20
**Domain:** React charting (Recharts), dark mode theming (next-themes + Tailwind v4), sortable data tables
**Confidence:** HIGH

## Summary

Phase 6 adds two features to the existing frontend: (1) an interactive price history view (line chart + sortable table) accessible from the QuerySheet slide-over, and (2) a dark/light mode toggle using next-themes (already installed but not wired). The existing codebase provides strong integration points -- ListingRow has a "View history" stub, QuerySheet manages slide-over state, the API endpoint `GET /retailer-urls/{retailer_url_id}/history` returns newest-first records with all needed fields, and shadcn/ui Table components are already available.

Recharts is the charting library (locked decision from CONTEXT.md). It provides `LineChart`, `Line`, `ReferenceLine` (for threshold dashed line), `XAxis`, `YAxis`, `Tooltip`, and `ResponsiveContainer` out of the box. The current version is 2.15.x (latest npm: 3.8.0 -- but the project context specifies Recharts without version lock, so use latest stable). For dark mode, Tailwind CSS v4 uses `@custom-variant dark (&:where(.dark, .dark *))` instead of the old `darkMode: 'class'` config. next-themes v0.4.6 (already in package.json) handles class toggling and localStorage persistence.

**Primary recommendation:** Install Recharts, build a `PriceHistoryView` component with stacked chart+table layout, wire `useListingHistory` hook to existing API, and implement dark mode via `@custom-variant` in index.css with next-themes ThemeProvider wrapping the app root.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Clicking "View history" on a listing row **replaces the slide-over content** with a history view for that listing
- A back button at the top returns to the listings view (no full close/reopen)
- History header shows: **product name + retailer domain** (e.g., "Sony WH-1000XM5 - amazon.com")
- If no scrape history exists: show empty state -- "No history yet -- trigger a scrape to start tracking."
- **Stacked layout:** chart on top, table below -- single scroll, everything visible at once
- **Time range filter** (7d / 30d / 90d / all) sits above the chart as segmented buttons; applies to both chart and table simultaneously
- Chart: line chart with horizontal dashed threshold line overlay (HIST-03)
- Table: date, price, delta columns -- default sort newest-first; clickable column headers to re-sort (HIST-04, HIST-05)
- **Frontend filtering:** fetch full history once on view open, filter client-side when user switches ranges

### Claude's Discretion
- Dark mode implementation: keep current dark terminal palette as "dark" mode, add a light theme, wire up next-themes (already installed); toggle location and light theme aesthetic are Claude's call
- Chart library: Recharts (as specified in roadmap plans 06-01)
- Exact chart styling: line color, dot size, tooltip design, threshold line dash pattern
- Table sort icon treatment and active sort indicator
- Loading skeleton while history fetches

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HIST-03 | Price history displayed as line chart with horizontal dashed threshold line overlay | Recharts LineChart + ReferenceLine with strokeDasharray; threshold_cents passed from QuerySheet parent |
| HIST-04 | Price history displayed as sortable table with date, price, delta columns (default: newest first) | shadcn Table component already available; client-side sort with React state; existing formatPrice/deltaIcon utils |
| HIST-05 | User can filter price history by time range (7d, 30d, 90d, all) | Client-side date filtering on fetched-once data; segmented button component above chart |
| UI-02 | Application supports dark mode toggle | next-themes v0.4.6 already installed; Tailwind v4 @custom-variant for class-based dark mode; light theme CSS variables in index.css |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | ^3.8.0 | Line chart with reference lines, tooltips, responsive container | De facto React charting library; composable API; works with CSS variables for theming |
| next-themes | 0.4.6 | Theme toggling (dark/light/system), localStorage persistence, class injection | Already installed in project; standard shadcn/ui companion for theming |

### Supporting (already in project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query | ^5.91.2 | Data fetching for history endpoint | useListingHistory hook follows existing pattern |
| lucide-react | ^0.577.0 | Icons for sort indicators, back button, theme toggle (Sun/Moon) | Already used throughout; ArrowLeft, ArrowUpDown, Sun, Moon |
| shadcn/ui Table | (bundled) | Sortable history table | Already generated in project at components/ui/table.tsx |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Recharts | Nivo, Victory, Chart.js | Recharts is locked decision; best React-native composable API |
| next-themes | Custom context | next-themes already installed; handles edge cases (SSR flash, system preference, localStorage) |
| Client-side sort | TanStack Table | Overkill for 3-column table with simple sort; plain useState sort is sufficient |

**Installation:**
```bash
cd frontend && npm install recharts
```

**Version verification:** recharts 3.8.0 confirmed via `npm view recharts version` on 2026-03-20. next-themes 0.4.6 already in package.json.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── components/
│   ├── history/
│   │   ├── PriceHistoryView.tsx    # Container: back button + header + filter + chart + table
│   │   ├── PriceChart.tsx          # Recharts LineChart + ReferenceLine
│   │   ├── PriceTable.tsx          # Sortable table with date/price/delta
│   │   └── TimeRangeFilter.tsx     # Segmented 7d/30d/90d/all buttons
│   ├── layout/
│   │   └── ThemeToggle.tsx         # Sun/Moon toggle button
│   └── query/
│       ├── QuerySheet.tsx          # Modified: conditionally renders listings OR history
│       └── ListingRow.tsx          # Modified: "View history" becomes clickable
├── hooks/
│   └── use-watch-queries.ts        # Add useListingHistory hook
├── lib/
│   ├── api.ts                      # Add retailerUrls.history() method
│   └── format.ts                   # Add formatDate() for table display
├── types/
│   └── api.ts                      # Add HistoryRecord type
└── index.css                       # Add light theme variables + @custom-variant
```

### Pattern 1: Slide-Over Content Swapping
**What:** QuerySheet maintains `selectedListingId` state; when set, renders PriceHistoryView instead of the listing list.
**When to use:** When the slide-over needs to show detail views without closing/reopening.
**Example:**
```typescript
// QuerySheet.tsx
const [selectedListingId, setSelectedListingId] = useState<number | null>(null);

// In render:
{selectedListingId ? (
  <PriceHistoryView
    retailerUrlId={selectedListingId}
    thresholdCents={detail.threshold_cents}
    onBack={() => setSelectedListingId(null)}
  />
) : (
  // existing listing list
)}
```

### Pattern 2: Client-Side Time Range Filtering
**What:** Fetch all history once, filter by date in component state. Avoids extra API calls per range switch.
**When to use:** When dataset is small enough for full fetch (price history for a single listing is bounded).
**Example:**
```typescript
type TimeRange = "7d" | "30d" | "90d" | "all";

function filterByRange(records: HistoryRecord[], range: TimeRange): HistoryRecord[] {
  if (range === "all") return records;
  const days = { "7d": 7, "30d": 30, "90d": 90 }[range];
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return records.filter(r => new Date(r.scraped_at) >= cutoff);
}
```

### Pattern 3: Tailwind v4 Dark Mode with CSS Variables
**What:** Define light theme overrides under `.dark` class removal (i.e., define light values as default when not `.dark`), use `@custom-variant` for Tailwind dark: prefix.
**When to use:** Tailwind CSS v4 projects using class-based dark mode.
**Example:**
```css
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

@layer base {
  :root {
    /* Light theme values */
    --color-background: oklch(0.98 0.005 264);
    --color-foreground: oklch(0.15 0.015 264);
    /* ... other light values ... */
  }

  .dark {
    /* Current dark terminal palette (already exists in @theme) */
    --color-background: oklch(0.11 0.018 264);
    --color-foreground: oklch(0.93 0.005 264);
    /* ... existing dark values ... */
  }
}
```

### Anti-Patterns to Avoid
- **Fetching history per range change:** The API has no range parameter; fetching the full set once and filtering client-side is the locked decision. Do not add backend range params.
- **Using `dark:` utility classes everywhere:** Since the project uses CSS variable theming, colors automatically adapt. Only use `dark:` for structural differences (e.g., different shadow intensities).
- **Recharts hardcoded colors:** Use CSS variable references (`var(--color-primary)`) for chart colors so they adapt to theme changes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Line chart rendering | Custom SVG/Canvas chart | Recharts `LineChart` + `Line` + `ReferenceLine` | Axis scaling, tooltips, responsive sizing, animation are complex |
| Theme persistence + class toggling | Custom localStorage + effect | next-themes ThemeProvider | Handles SSR flash prevention, system preference detection, class injection |
| Sortable table | Custom sort + accessibility | shadcn Table + useState sort logic | Table component handles styling; sort is just `Array.sort()` in state |
| Responsive chart container | Manual resize observer | Recharts `ResponsiveContainer` | Handles width/height recalculation on resize |

**Key insight:** Recharts and next-themes are purpose-built for exactly these use cases. The chart especially has many edge cases (axis formatting, hover states, responsive sizing) that would take significant effort to hand-roll.

## Common Pitfalls

### Pitfall 1: Recharts ResponsiveContainer Height
**What goes wrong:** Chart renders with zero height because ResponsiveContainer needs an explicit height or a parent with defined height.
**Why it happens:** ResponsiveContainer uses the parent's dimensions; if the parent has no height, the chart collapses.
**How to avoid:** Always wrap in a div with explicit height: `<div style={{ width: '100%', height: 300 }}><ResponsiveContainer>...</ResponsiveContainer></div>` or use `<ResponsiveContainer width="100%" height={300}>`.
**Warning signs:** Chart area is blank/invisible but no errors in console.

### Pitfall 2: Price Cents vs Dollars in Chart
**What goes wrong:** Chart Y-axis shows raw cents (e.g., 99900) instead of dollars ($999.00).
**Why it happens:** API returns `price_cents` as integer. Recharts plots raw data values.
**How to avoid:** Transform data before passing to chart: `data.map(r => ({ ...r, price: r.price_cents / 100 }))`. Format Y-axis tick with `tickFormatter={(v) => formatPrice(v * 100)}` or use dollars directly.
**Warning signs:** Y-axis labels show large integers.

### Pitfall 3: Threshold Line Also Needs Cents-to-Dollars Conversion
**What goes wrong:** Threshold reference line appears at wrong position.
**Why it happens:** If chart data uses dollars but threshold is still in cents (or vice versa).
**How to avoid:** Ensure threshold_cents is converted to the same unit as chart data: `<ReferenceLine y={thresholdCents / 100} />`.

### Pitfall 4: Tailwind v4 @theme vs @layer base for Dark Mode
**What goes wrong:** CSS variables defined in `@theme` cannot be overridden by `.dark` class selector.
**Why it happens:** `@theme` in Tailwind v4 defines design tokens at a high specificity. To override per-theme, variables need to be in `@layer base` or `:root`/`.dark` selectors.
**How to avoid:** Move CSS variable definitions from `@theme` to `:root` (light) and `.dark` (dark) inside `@layer base`. Keep `@theme` only for non-theme-varying tokens (radius, font families).
**Warning signs:** Dark mode colors don't change when toggling theme.

### Pitfall 5: next-themes Flash of Wrong Theme
**What goes wrong:** Page briefly shows light theme before switching to dark (or vice versa).
**Why it happens:** React hydration happens after initial paint; theme class is applied after render.
**How to avoid:** next-themes injects a script tag that sets the class before React hydrates. Ensure ThemeProvider wraps the entire app and `attribute="class"` is set. For Vite (no SSR), this is less of an issue but still set `defaultTheme="dark"` to match the current-only-dark state.

### Pitfall 6: Recharts Colors Not Updating on Theme Change
**What goes wrong:** Chart colors remain the same after theme toggle.
**Why it happens:** Recharts renders SVG with inline styles; CSS variables in SVG attributes may not trigger re-render.
**How to avoid:** Use CSS variable values resolved at render time, or pass theme-aware colors as props. If using `stroke="var(--color-primary)"`, this works in SVG `stroke` attribute. Test both themes.

## Code Examples

### History API Hook (following existing TanStack Query pattern)
```typescript
// In use-watch-queries.ts
export const queryKeys = {
  // ...existing keys
  listingHistory: (retailerUrlId: number) =>
    ["listing-history", retailerUrlId] as const,
};

export function useListingHistory(retailerUrlId: number | null) {
  return useQuery({
    queryKey: queryKeys.listingHistory(retailerUrlId!),
    queryFn: () => api.retailerUrls.history(retailerUrlId!),
    enabled: retailerUrlId !== null,
  });
}
```

### API Client Extension
```typescript
// In api.ts - add to exports
retailerUrls: {
  history: (id: number) =>
    apiFetch<HistoryRecord[]>(`/retailer-urls/${id}/history`),
},
```

### History Record Type (matching backend HistoryRecordResponse)
```typescript
// In types/api.ts
export interface HistoryRecord {
  id: number;
  product_name: string;
  price_cents: number;
  retailer_name: string;
  listing_url: string;
  scraped_at: string;
  direction: "new" | "higher" | "lower" | "unchanged";
  delta_cents: number;
  pct_change: number;
}
```

### Recharts Line Chart with Dashed Threshold Line
```typescript
// Source: Recharts API docs - ReferenceLine
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ReferenceLine, ResponsiveContainer, CartesianGrid,
} from "recharts";

<ResponsiveContainer width="100%" height={300}>
  <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
    <XAxis
      dataKey="date"
      tick={{ fontSize: 12, fill: "var(--color-muted-foreground)" }}
    />
    <YAxis
      tickFormatter={(v) => `$${v.toFixed(0)}`}
      tick={{ fontSize: 12, fill: "var(--color-muted-foreground)" }}
    />
    <Tooltip
      formatter={(value: number) => [`$${value.toFixed(2)}`, "Price"]}
      contentStyle={{
        backgroundColor: "var(--color-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius)",
      }}
    />
    <ReferenceLine
      y={thresholdDollars}
      stroke="var(--color-destructive)"
      strokeDasharray="8 4"
      label={{ value: "Threshold", position: "right", fill: "var(--color-destructive)" }}
    />
    <Line
      type="monotone"
      dataKey="price"
      stroke="var(--color-primary)"
      strokeWidth={2}
      dot={{ r: 3, fill: "var(--color-primary)" }}
      activeDot={{ r: 5 }}
    />
  </LineChart>
</ResponsiveContainer>
```

### Tailwind v4 Dark Mode CSS Setup
```css
/* index.css */
@import url("https://fonts.googleapis.com/css2?family=...");
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

@theme {
  --font-body: "DM Sans", sans-serif;
  --font-heading: "Outfit", sans-serif;
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
  --radius: 0.625rem;
}

@layer base {
  /* Light theme (default when .dark class is absent) */
  :root {
    --color-background: oklch(0.98 0.005 264);
    --color-foreground: oklch(0.15 0.015 264);
    /* ... all light values */
  }

  /* Dark theme (current palette, applied when .dark class present) */
  .dark {
    --color-background: oklch(0.11 0.018 264);
    --color-foreground: oklch(0.93 0.005 264);
    /* ... all existing dark values */
  }
}
```

### next-themes ThemeProvider Setup
```typescript
// main.tsx
import { ThemeProvider } from "next-themes";

<ThemeProvider attribute="class" defaultTheme="dark" storageKey="price-scraper-theme">
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <App />
      <Toaster position="bottom-right" richColors closeButton />
    </BrowserRouter>
  </QueryClientProvider>
</ThemeProvider>
```

### Theme Toggle Component
```typescript
// Source: shadcn/ui dark mode docs for Vite
import { useTheme } from "next-themes";
import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:rotate-90 dark:scale-0" />
      <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tailwind v3 `darkMode: 'class'` in config | Tailwind v4 `@custom-variant dark (...)` in CSS | Tailwind v4 (2025) | No config file needed; CSS-first approach |
| Recharts 2.x | Recharts 3.x | 2025 | API largely same; improved tree-shaking and TypeScript |
| Manual theme context | next-themes ThemeProvider | Stable since 2023 | Handles flash prevention, system preference, persistence |

**Deprecated/outdated:**
- `tailwind.config.js` `darkMode` key: Replaced by `@custom-variant` in Tailwind v4
- Recharts 2.x: Still works but 3.x is current; API is backward-compatible

## Open Questions

1. **Recharts CSS variable support in SVG**
   - What we know: SVG `stroke` and `fill` attributes accept `var(--css-variable)` in modern browsers
   - What's unclear: Whether Recharts internal styles properly cascade CSS variables for all sub-elements (tooltips, labels)
   - Recommendation: Test with both themes during implementation; fall back to resolved color values if CSS vars don't work in specific Recharts elements

2. **Light theme palette design**
   - What we know: Current dark palette is well-established with oklch values; light theme needs complementary values
   - What's unclear: Exact light theme colors (Claude's discretion per CONTEXT.md)
   - Recommendation: Create light palette that inverts luminance while keeping same hue/chroma ratios; test readability

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 4.1.0 + @testing-library/react 16.3.2 |
| Config file | `frontend/vitest.config.ts` |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run --reporter=verbose` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HIST-03 | Line chart renders with threshold reference line | unit | `cd frontend && npx vitest run src/__tests__/PriceChart.test.tsx -x` | No - Wave 0 |
| HIST-04 | Sortable table renders with date/price/delta, default newest-first | unit | `cd frontend && npx vitest run src/__tests__/PriceTable.test.tsx -x` | No - Wave 0 |
| HIST-05 | Time range filter filters data by 7d/30d/90d/all | unit | `cd frontend && npx vitest run src/__tests__/PriceHistoryView.test.tsx -x` | No - Wave 0 |
| UI-02 | Theme toggle switches between dark and light mode | unit | `cd frontend && npx vitest run src/__tests__/ThemeToggle.test.tsx -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd frontend && npx vitest run --reporter=verbose`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `src/__tests__/PriceChart.test.tsx` -- covers HIST-03 (chart renders, threshold line present)
- [ ] `src/__tests__/PriceTable.test.tsx` -- covers HIST-04 (table renders, sort toggles work)
- [ ] `src/__tests__/PriceHistoryView.test.tsx` -- covers HIST-05 (time range filtering)
- [ ] `src/__tests__/ThemeToggle.test.tsx` -- covers UI-02 (toggle switches theme class)
- [ ] `recharts` package install: `cd frontend && npm install recharts`

## Sources

### Primary (HIGH confidence)
- Tailwind CSS v4 official docs -- dark mode `@custom-variant` syntax: https://tailwindcss.com/docs/dark-mode
- shadcn/ui Vite dark mode guide: https://ui.shadcn.com/docs/dark-mode/vite
- Recharts API docs -- ReferenceLine: https://recharts.github.io/en-US/api/ReferenceLine/
- Recharts examples -- Line Chart with Reference Lines: https://recharts.github.io/en-US/examples/LineChartWithReferenceLines/
- npm registry -- recharts 3.8.0, next-themes 0.4.6 (verified 2026-03-20)

### Secondary (MEDIUM confidence)
- next-themes GitHub repository: https://github.com/pacocoursey/next-themes
- Recharts dashed line example: https://recharts.github.io/en-US/examples/DashedLineChart/

### Tertiary (LOW confidence)
- Recharts CSS variable behavior in SVG -- needs validation during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Recharts is locked decision, next-themes already installed, versions verified via npm
- Architecture: HIGH - Existing codebase patterns (QuerySheet, ListingRow, TanStack Query hooks) clearly establish integration points
- Pitfalls: HIGH - Recharts ResponsiveContainer height and cents-vs-dollars are well-documented; Tailwind v4 dark mode syntax verified against official docs
- Dark mode CSS approach: MEDIUM - Tailwind v4 @theme vs @layer base interaction for variable overrides needs careful implementation

**Research date:** 2026-03-20
**Valid until:** 2026-04-20 (stable libraries, no fast-moving changes expected)
