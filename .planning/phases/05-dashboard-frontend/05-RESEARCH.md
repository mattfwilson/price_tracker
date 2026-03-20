# Phase 5: Dashboard Frontend - Research

**Researched:** 2026-03-19
**Domain:** React SPA with shadcn/ui, TanStack Query, SSE integration
**Confidence:** HIGH

## Summary

Phase 5 builds a React + Vite + TypeScript single-page application that consumes the FastAPI backend APIs from Phases 1-4. The UI spec and context documents are exceptionally detailed -- they prescribe every component, interaction, color, and copy string. The research focus is on verifying the correct current tooling versions, identifying the right patterns for data fetching/state management, SSE integration with TanStack Query, and surfacing a critical API gap in the list endpoint.

The stack is fully locked by user decisions and the UI spec: React 19, Vite, TypeScript, Tailwind CSS v4, shadcn/ui (default zinc preset), TanStack React Query, React Router, lucide-react icons, and Sonner for toasts. shadcn/ui v4.1.0 now supports Tailwind v4 natively with a single `shadcn init` command that scaffolds the entire project.

**Primary recommendation:** Use `npx shadcn@latest init -t vite` to scaffold the project (handles Tailwind v4, path aliases, CSS variables), then add all 15 shadcn components in batch. Build a typed API client layer with fetch (no axios needed for this scope), wire TanStack Query for all server state, and use native EventSource for SSE with a custom hook that pushes alerts into the query cache.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Two routes: `/` (dashboard) and `/alerts` (alert log page)
- Drill-down opens as a slide-over panel (Sheet) on top of the dashboard (no route change)
- React Router required for the two routes
- Header: app name left, notification bell with unread badge right. No sidebar.
- Bell icon opens dropdown panel inline (Popover), not navigation. "View all" link routes to /alerts.
- Card grid layout: 2-3 columns desktop, 1 mobile. Responsive.
- Card content: query name, URL count, three-dot menu, lowest price + delta, threshold, status dot + label + timestamp
- Threshold-breached: green border + "Below threshold" badge (DASH-02)
- Card body click opens drill-down slide-over
- Three-dot menu: Edit, Pause/Resume, Scrape Now, Delete
- "+ New Query" card as last card in grid
- Slide-over: header with query name/threshold/status, listing rows with product name/price/delta/"Lowest" badge, disabled "View history" link
- Create/Edit use same modal Dialog, pre-filled for edit
- Form fields: Name, Threshold (dollars -> cents conversion), Schedule dropdown, dynamic URL list
- Delete: simple AlertDialog confirmation
- Bell dropdown: 5-10 recent alerts, unread dot, click marks read, "Dismiss all" + "View all"
- Toast: bottom-right, auto-dismiss 5s, from SSE stream
- Alert log: table layout, newest first, click row marks read, "Dismiss All" button
- shadcn/ui with default zinc preset, Radix UI via shadcn, lucide-react icons
- Fonts: "DM Sans" (body) + "Outfit" (headings) via Google Fonts

### Claude's Discretion
- Exact Tailwind class choices, spacing, typography
- Whether to use a headless UI library (Radix, Headless UI) or build primitives from scratch -- RESOLVED: shadcn/ui uses Radix underneath, so Radix is the answer
- TanStack Query cache invalidation strategy (refetch vs optimistic update)
- SSE reconnect/error handling strategy
- Loading skeletons vs spinner during data fetch -- RESOLVED by UI spec: skeletons
- Error state handling (API errors, network errors)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | Dashboard displays all active watch queries with query name, lowest current price, last scrape timestamp, scrape status | Card grid consuming `GET /watch-queries/` + detail fetches; TanStack Query for caching; status indicator mapping from UI spec |
| DASH-02 | Queries at/below threshold visually highlighted | Emerald-500 left border + "Below threshold" Badge per UI spec; compare lowest `price_cents` against `threshold_cents` client-side |
| DASH-03 | Drill-down into watch query showing listings, prices, deltas, price history navigation | Sheet component consuming `GET /watch-queries/{id}` detail; "View history" link disabled in Phase 5 |
| DASH-04 | Scrape status indicator (success/error/running/paused) per card | Status dot color mapping from UI spec; derive from `is_active` + latest scrape result presence/absence |
| UI-01 | Lowest-price listing highlighted across retailer URLs in drill-down | Client-side `Math.min()` over `latest_result.price_cents` array; "Lowest" Badge on matching row |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 19.2.4 | UI framework | Latest stable; shadcn/ui compatible |
| react-dom | 19.2.4 | DOM rendering | Matches React version |
| vite | 8.0.1 | Build tool + dev server | Official shadcn/ui Vite template; HMR on port 5173 (matches CORS config) |
| typescript | 5.9.3 | Type safety | Vite template default |
| tailwindcss | 4.2.2 | Utility-first CSS | shadcn/ui requires it; v4 uses `@tailwindcss/vite` plugin |
| @tailwindcss/vite | 4.2.2 | Tailwind Vite integration | Required for Tailwind v4 (replaces PostCSS plugin) |
| shadcn | 4.1.0 | CLI for component generation | Scaffolds project + adds components from registry |
| @tanstack/react-query | 5.91.2 | Server state management | De facto standard for REST API data fetching/caching |
| react-router-dom | 7.13.1 | Client routing | Two routes: `/` and `/alerts` |
| lucide-react | 0.577.0 | Icons | Specified in UI spec; shadcn/ui default icon library |
| sonner | 2.0.7 | Toast notifications | shadcn/ui Sonner component wraps this |
| zod | 4.3.6 | Form validation schemas | Type-safe validation for CRUD forms |

### Supporting (via shadcn/ui -- installed automatically)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @radix-ui/react-dialog | 1.1.15 | Dialog primitive | CRUD modal |
| @radix-ui/react-alert-dialog | 1.1.15 | Alert dialog primitive | Delete confirmation |
| @radix-ui/react-dropdown-menu | 2.1.16 | Dropdown primitive | Three-dot card menu |
| @radix-ui/react-popover | 1.1.15 | Popover primitive | Bell notification dropdown |
| @radix-ui/react-select | 2.2.6 | Select primitive | Schedule dropdown |
| @radix-ui/react-separator | 1.1.8 | Separator primitive | Dividers |
| class-variance-authority | 0.7.1 | Variant styling | shadcn component variants |
| clsx | 2.1.1 | Conditional classnames | shadcn cn() utility |
| tailwind-merge | 3.5.0 | Tailwind class merging | shadcn cn() utility |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| fetch (built-in) | axios | Axios adds bundle weight for features unused here (interceptors, transforms); fetch + TanStack Query is sufficient |
| zod | react-hook-form + yup | Zod integrates better with TypeScript inference; lighter for this form scope |
| Native EventSource | @microsoft/fetch-event-source | Native EventSource is sufficient for GET-only SSE; the MS library adds POST support we don't need |

**Installation:**
```bash
# Project scaffold (creates Vite + React + TS + Tailwind v4 + shadcn config)
npx shadcn@latest init -t vite

# Additional dependencies
npm install @tanstack/react-query react-router-dom zod

# shadcn components (batch add)
npx shadcn@latest add card dialog alert-dialog dropdown-menu button input label select badge table popover skeleton sonner sheet separator
```

**Version verification:** All versions verified against npm registry on 2026-03-19.

## Architecture Patterns

### Recommended Project Structure
```
frontend/
├── index.html
├── vite.config.ts
├── components.json            # shadcn config
├── tsconfig.json
├── package.json
├── src/
│   ├── main.tsx               # React root + providers
│   ├── App.tsx                # Router layout
│   ├── index.css              # Tailwind v4 import + Google Fonts + custom vars
│   ├── lib/
│   │   ├── utils.ts           # cn() helper (shadcn default)
│   │   ├── api.ts             # Typed fetch wrapper (base URL, error handling)
│   │   └── format.ts          # formatPrice(), formatRelativeTime(), deltaIcon()
│   ├── types/
│   │   └── api.ts             # TypeScript interfaces mirroring backend schemas
│   ├── hooks/
│   │   ├── use-watch-queries.ts   # TanStack Query hooks for watch query CRUD
│   │   ├── use-alerts.ts          # TanStack Query hooks for alerts
│   │   └── use-sse.ts             # SSE connection hook with reconnect
│   ├── components/
│   │   ├── ui/                # shadcn-generated components (do not edit)
│   │   ├── layout/
│   │   │   ├── Header.tsx     # App name + bell icon
│   │   │   └── Layout.tsx     # Header + Outlet wrapper
│   │   ├── dashboard/
│   │   │   ├── QueryCard.tsx      # Individual watch query card
│   │   │   ├── QueryCardGrid.tsx  # Grid container + empty state + "+" card
│   │   │   ├── StatusDot.tsx      # Colored status indicator
│   │   │   └── CardMenu.tsx       # Three-dot dropdown menu
│   │   ├── query/
│   │   │   ├── QuerySheet.tsx     # Slide-over drill-down panel
│   │   │   ├── ListingRow.tsx     # Single listing in drill-down
│   │   │   └── QueryFormDialog.tsx # Create/edit modal
│   │   ├── alerts/
│   │   │   ├── BellDropdown.tsx   # Bell icon + popover
│   │   │   ├── AlertToast.tsx     # SSE-triggered toast handler
│   │   │   └── AlertLogTable.tsx  # Full alert log table
│   │   └── shared/
│   │       ├── EmptyState.tsx     # Reusable empty state component
│   │       └── ErrorState.tsx     # API error display
│   └── pages/
│       ├── DashboardPage.tsx  # "/" route
│       └── AlertsPage.tsx     # "/alerts" route
```

### Pattern 1: Typed API Client with fetch
**What:** A thin wrapper around fetch that handles base URL, JSON parsing, and error responses. No axios.
**When to use:** Every API call.
**Example:**
```typescript
// src/lib/api.ts
const API_BASE = "http://localhost:8000";

class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  watchQueries: {
    list: () => apiFetch<WatchQueryResponse[]>("/watch-queries/"),
    detail: (id: number) => apiFetch<WatchQueryDetailResponse>(`/watch-queries/${id}`),
    create: (data: WatchQueryCreate) =>
      apiFetch<WatchQueryResponse>("/watch-queries/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: number, data: WatchQueryUpdate) =>
      apiFetch<WatchQueryResponse>(`/watch-queries/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      apiFetch<void>(`/watch-queries/${id}`, { method: "DELETE" }),
    pause: (id: number) =>
      apiFetch<WatchQueryResponse>(`/watch-queries/${id}/pause`, { method: "PATCH" }),
    resume: (id: number) =>
      apiFetch<WatchQueryResponse>(`/watch-queries/${id}/resume`, { method: "PATCH" }),
    scrape: (id: number) =>
      apiFetch<ScrapeJobResponse>(`/watch-queries/${id}/scrape`, { method: "POST" }),
  },
  alerts: {
    list: (limit?: number) => apiFetch<AlertResponse[]>(`/alerts/?limit=${limit ?? 50}`),
    unreadCount: () => apiFetch<UnreadCountResponse>("/alerts/unread-count"),
    markRead: (id: number) =>
      apiFetch<AlertResponse>(`/alerts/${id}/read`, { method: "PATCH" }),
    dismissAll: () => apiFetch<{ dismissed_count: number }>("/alerts/dismiss-all", { method: "POST" }),
  },
};
```

### Pattern 2: TanStack Query Hooks with Mutation Invalidation
**What:** Custom hooks wrapping useQuery/useMutation that handle cache invalidation automatically.
**When to use:** All data fetching and mutations.
**Example:**
```typescript
// src/hooks/use-watch-queries.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export const queryKeys = {
  watchQueries: ["watch-queries"] as const,
  watchQueryDetail: (id: number) => ["watch-queries", id] as const,
  alerts: ["alerts"] as const,
  unreadCount: ["alerts", "unread-count"] as const,
};

export function useWatchQueries() {
  return useQuery({
    queryKey: queryKeys.watchQueries,
    queryFn: api.watchQueries.list,
  });
}

export function useWatchQueryDetail(id: number | null) {
  return useQuery({
    queryKey: queryKeys.watchQueryDetail(id!),
    queryFn: () => api.watchQueries.detail(id!),
    enabled: id !== null,
  });
}

export function useDeleteWatchQuery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.watchQueries.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.watchQueries });
    },
  });
}
```

### Pattern 3: SSE Hook with Query Cache Integration
**What:** A custom hook that opens an EventSource connection to the SSE endpoint and pushes incoming alerts into TanStack Query's cache, triggering re-renders.
**When to use:** Once, at the app root (Layout component).
**Example:**
```typescript
// src/hooks/use-sse.ts
import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "./use-watch-queries";
import { toast } from "sonner";
import { formatPrice } from "@/lib/format";

export function useAlertSSE() {
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const connect = () => {
      const es = new EventSource("http://localhost:8000/alerts/stream");
      eventSourceRef.current = es;

      es.addEventListener("alert", (event) => {
        const data = JSON.parse(event.data);

        // Update unread count in cache directly from SSE payload
        queryClient.setQueryData(queryKeys.unreadCount, {
          unread_count: data.unread_count,
        });

        // Invalidate alerts list to pick up new alert
        queryClient.invalidateQueries({ queryKey: queryKeys.alerts });

        // Show toast
        toast(`${data.watch_query_name} -- ${formatPrice(data.price_cents)} at ${data.retailer_name}`, {
          description: "Below threshold!",
          duration: 5000,
        });
      });

      es.onerror = () => {
        es.close();
        // Reconnect after 3 seconds
        setTimeout(connect, 3000);
      };
    };

    connect();
    return () => eventSourceRef.current?.close();
  }, [queryClient]);
}
```

### Pattern 4: Price Formatting Utility
**What:** Shared utility for cents-to-dollars conversion used everywhere.
**When to use:** Every price display.
**Example:**
```typescript
// src/lib/format.ts
export function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

export function deltaIcon(direction: string): string {
  switch (direction) {
    case "higher": return "\u2191"; // up arrow
    case "lower": return "\u2193";  // down arrow
    default: return "\u2014";       // em dash
  }
}
```

### Anti-Patterns to Avoid
- **Direct fetch in components:** Always go through TanStack Query hooks. Never `useEffect` + `fetch` + `useState` for API data.
- **Global state for server data:** Do not use React context or Zustand for data that lives on the server. TanStack Query IS the server state manager.
- **Prop drilling query results:** Pass query IDs down, let child components call their own hooks. TanStack Query deduplicates requests automatically.
- **Manual SSE state management:** Do not maintain a separate SSE state store. Push SSE data directly into TanStack Query cache so components reactively update.

## Critical Finding: Dashboard List Endpoint Gap

**Confidence: HIGH** (verified by reading backend source code)

The `GET /watch-queries/` list endpoint returns `WatchQueryResponse` which includes `retailer_urls` but does NOT include `latest_result` per URL. The detail endpoint `GET /watch-queries/{id}` returns `WatchQueryDetailResponse` which DOES include `latest_result`.

Dashboard cards need: lowest price, delta direction, last scrape timestamp, and threshold-breach detection -- all of which come from `latest_result`.

**Options (Claude's discretion -- recommend option B):**

| Option | Approach | Tradeoff |
|--------|----------|----------|
| A | Call detail endpoint for each query (N requests) | N+1 problem; slow with many queries; but data is small and local |
| B | Fetch list, then batch-fetch details with TanStack Query | Each card triggers its own `useWatchQueryDetail(id)` hook; TanStack Query deduplicates and caches; parallel requests; slide-over reuses cached detail |
| C | Modify backend list endpoint to include latest_result | Best performance but out of Phase 5 scope (backend change) |

**Recommendation: Option B.** Use `useWatchQueries()` to get the list of IDs/names, then each `QueryCard` component calls `useWatchQueryDetail(id)` independently. TanStack Query fires these in parallel, caches the results, and the slide-over drill-down reuses the already-cached detail. For a personal tool with <50 watch queries, this is perfectly performant over localhost. The card can show a skeleton for the price area while the detail loads.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modal/dialog accessibility | Custom overlay with portal | shadcn Dialog (Radix) | Focus trap, escape handling, screen readers, scroll lock |
| Dropdown menu | Custom div with click-away | shadcn DropdownMenu (Radix) | Keyboard nav, ARIA roles, submenu support |
| Toast system | Custom toast manager | Sonner (via shadcn) | Queue management, auto-dismiss, stacking, animations |
| Slide-over panel | Custom sidebar div | shadcn Sheet (Radix) | Overlay, animation, focus management, escape handling |
| Form validation | Manual if/else checks | Zod schemas | Type inference, composable, reusable between create/edit |
| Relative timestamps | Manual date math | `Intl.RelativeTimeFormat` or small helper | Edge cases with timezones, "just now" vs "1m ago" |
| Class name merging | String concatenation | cn() utility (clsx + tailwind-merge) | Resolves Tailwind class conflicts correctly |

**Key insight:** shadcn/ui provides all 15 required UI primitives as copy-pasted source code. They are not a dependency -- they live in `src/components/ui/` and can be customized. The underlying Radix primitives handle all accessibility and interaction edge cases.

## Common Pitfalls

### Pitfall 1: Tailwind v4 CSS Import Syntax
**What goes wrong:** Using old `@tailwind base; @tailwind components; @tailwind utilities;` directives.
**Why it happens:** Tailwind v4 changed the import syntax.
**How to avoid:** Use `@import "tailwindcss";` as the single import in `index.css`. The shadcn init command handles this automatically.
**Warning signs:** Styles not applying, PostCSS errors.

### Pitfall 2: CORS Mismatch with Vite Dev Server
**What goes wrong:** API requests blocked by browser CORS policy.
**Why it happens:** Backend CORS allows `http://localhost:5173` and `http://localhost:3000`. If Vite runs on a different port, requests fail.
**How to avoid:** Ensure Vite config uses default port 5173 (which it does by default). Do NOT proxy API requests through Vite -- make direct cross-origin requests since CORS is properly configured.
**Warning signs:** Browser console shows CORS errors on fetch requests.

### Pitfall 3: SSE EventSource Event Type Mismatch
**What goes wrong:** EventSource `onmessage` handler never fires.
**Why it happens:** Backend sends `event: alert\n` with a named event type. The `onmessage` handler only catches events without a type (or type "message"). Named events need `addEventListener("alert", ...)`.
**How to avoid:** Use `es.addEventListener("alert", callback)` not `es.onmessage = callback`.
**Warning signs:** SSE connection opens but no alerts appear. Network tab shows events arriving.

### Pitfall 4: Stale Closure in SSE Handler
**What goes wrong:** SSE handler captures stale queryClient reference or stale state.
**Why it happens:** useEffect closure captures values from render time.
**How to avoid:** Use `useRef` for the EventSource instance. The `queryClient` from `useQueryClient()` is stable (same reference across renders), so it's safe in the effect.
**Warning signs:** First alert works, subsequent alerts don't update UI.

### Pitfall 5: Form Dollar-to-Cents Conversion
**What goes wrong:** User enters "$400" but API receives 400 (should be 40000 cents).
**Why it happens:** Forgetting the cents conversion on form submit.
**How to avoid:** Form input accepts dollar values (e.g., "400.00"). On submit, multiply by 100 and round: `Math.round(parseFloat(value) * 100)`. On edit form population, divide by 100.
**Warning signs:** All threshold comparisons are off by 100x.

### Pitfall 6: Three-Dot Menu Click Propagation
**What goes wrong:** Clicking the three-dot menu or its items also triggers the card click (opens slide-over).
**Why it happens:** Click events bubble up from the dropdown trigger to the card container.
**How to avoid:** Add `onClick={(e) => e.stopPropagation()}` on the DropdownMenu trigger button.
**Warning signs:** Opening the menu also opens the slide-over panel.

## Code Examples

### Google Fonts Setup in CSS (Tailwind v4)
```css
/* src/index.css */
@import "tailwindcss";
@import url("https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700&family=Outfit:wght@700&display=swap");

@theme {
  --font-body: "DM Sans", sans-serif;
  --font-heading: "Outfit", sans-serif;
}
```

### TypeScript API Types (Mirror Backend Schemas)
```typescript
// src/types/api.ts
export interface RetailerUrlResponse {
  id: number;
  url: string;
  created_at: string;
}

export interface LatestScrapeResult {
  product_name: string;
  price_cents: number;
  listing_url: string;
  scraped_at: string;
  direction: "new" | "higher" | "lower" | "unchanged";
  delta_cents: number;
  pct_change: number;
}

export interface RetailerUrlWithLatest {
  id: number;
  url: string;
  created_at: string;
  latest_result: LatestScrapeResult | null;
}

export interface WatchQueryResponse {
  id: number;
  name: string;
  threshold_cents: number;
  is_active: boolean;
  schedule: string;
  retailer_urls: RetailerUrlResponse[];
  created_at: string;
  updated_at: string;
}

export interface WatchQueryDetailResponse {
  id: number;
  name: string;
  threshold_cents: number;
  is_active: boolean;
  schedule: string;
  retailer_urls: RetailerUrlWithLatest[];
  created_at: string;
  updated_at: string;
}

export interface WatchQueryCreate {
  name: string;
  threshold_cents: number;
  urls: string[];
  schedule: string;
}

export interface WatchQueryUpdate {
  name?: string;
  threshold_cents?: number;
  is_active?: boolean;
  schedule?: string;
  urls?: string[];
}

export interface AlertResponse {
  id: number;
  watch_query_id: number;
  watch_query_name: string;
  product_name: string;
  price_cents: number;
  retailer_name: string;
  listing_url: string;
  is_read: boolean;
  created_at: string;
}

export interface AlertSSEPayload {
  alert_id: number;
  watch_query_id: number;
  watch_query_name: string;
  product_name: string;
  price_cents: number;
  retailer_name: string;
  listing_url: string;
  created_at: string;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export interface ScrapeJobResponse {
  job_id: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  results: ScrapeResultResponse[];
}

export interface ScrapeResultResponse {
  product_name: string;
  price_cents: number;
  retailer_name: string;
  listing_url: string;
  scraped_at: string;
  direction: string;
  delta_cents: number;
  pct_change: number;
}
```

### Threshold Breach Detection (Client-Side)
```typescript
// Used in QueryCard to determine if card should show green border + badge
function isThresholdBreached(detail: WatchQueryDetailResponse): boolean {
  const prices = detail.retailer_urls
    .map((u) => u.latest_result?.price_cents)
    .filter((p): p is number => p !== undefined);
  if (prices.length === 0) return false;
  return Math.min(...prices) <= detail.threshold_cents;
}
```

### Lowest Price Detection (Client-Side)
```typescript
// Used in QuerySheet drill-down to badge the lowest-price listing
function findLowestPriceUrlId(urls: RetailerUrlWithLatest[]): number | null {
  let lowestId: number | null = null;
  let lowestPrice = Infinity;
  for (const url of urls) {
    if (url.latest_result && url.latest_result.price_cents < lowestPrice) {
      lowestPrice = url.latest_result.price_cents;
      lowestId = url.id;
    }
  }
  return lowestId;
}
```

### App Root with Providers
```typescript
// src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30s before refetch
      refetchOnWindowFocus: true,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
        <Toaster position="bottom-right" richColors closeButton />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tailwind v3 (PostCSS + tailwind.config.js) | Tailwind v4 (@tailwindcss/vite plugin + @import "tailwindcss") | Jan 2025 | No config file needed; CSS-first configuration via @theme |
| shadcn init (manual steps) | `shadcn init -t vite` (template flag) | shadcn 4.x | Single command scaffolds entire project |
| Create React App | Vite | 2022+ | CRA is unmaintained; Vite is the standard |
| React Router v6 | React Router v7 | 2024 | New data loader patterns (optional; not needed for this simple 2-route app) |
| TanStack Query v4 | TanStack Query v5 | 2023 | Simplified API, better TypeScript inference |

**Deprecated/outdated:**
- Create React App: Unmaintained since 2023. Use Vite.
- Tailwind `@apply` in config files: v4 uses CSS `@theme` directive instead.
- `tailwind.config.js`: v4 is CSS-first; theme customization goes in CSS `@theme` blocks.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest (bundled with Vite) + React Testing Library |
| Config file | `frontend/vitest.config.ts` (Wave 0 creation) |
| Quick run command | `cd frontend && npx vitest run --reporter=verbose` |
| Full suite command | `cd frontend && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Dashboard renders query cards with name, price, timestamp, status | unit | `cd frontend && npx vitest run src/__tests__/DashboardPage.test.tsx -t "renders query cards"` | Wave 0 |
| DASH-02 | Threshold-breached cards show green border and badge | unit | `cd frontend && npx vitest run src/__tests__/QueryCard.test.tsx -t "threshold breach"` | Wave 0 |
| DASH-03 | Drill-down sheet shows listings with prices and deltas | unit | `cd frontend && npx vitest run src/__tests__/QuerySheet.test.tsx -t "listings"` | Wave 0 |
| DASH-04 | Status indicator shows correct color/label per state | unit | `cd frontend && npx vitest run src/__tests__/StatusDot.test.tsx` | Wave 0 |
| UI-01 | Lowest-price listing has "Lowest" badge | unit | `cd frontend && npx vitest run src/__tests__/QuerySheet.test.tsx -t "lowest badge"` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx vitest run --reporter=verbose`
- **Per wave merge:** `cd frontend && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/vitest.config.ts` -- Vitest configuration
- [ ] `frontend/src/test/setup.ts` -- Testing library setup (jsdom, cleanup)
- [ ] `frontend/src/__tests__/` -- Test directory
- [ ] Framework install: `npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom`

## Open Questions

1. **List endpoint lacks price data for cards**
   - What we know: `GET /watch-queries/` returns `WatchQueryResponse` without `latest_result`. Dashboard cards need price data.
   - What's unclear: Whether the N+1 detail fetch pattern will feel slow.
   - Recommendation: Use per-card `useWatchQueryDetail(id)` hooks (option B above). TanStack Query parallelizes and caches. For <50 queries over localhost, latency is negligible. If it feels slow later, the backend can add a `/watch-queries/?include=latest_results` query param in a future phase.

2. **Scrape status "running" detection**
   - What we know: Backend has no real-time scrape status push via SSE (SSE only sends alerts). There is no `is_running` field on `WatchQueryResponse`.
   - What's unclear: How to show the "Running" status dot on a card during an on-demand scrape.
   - Recommendation: Use local React state. When "Scrape Now" is clicked, set card to "Running" state optimistically. When the mutation completes (success or error), revert to the appropriate status. This is a UI-only concern.

3. **Pause/Resume endpoint shape**
   - What we know: CONTEXT.md lists `PATCH /watch-queries/{id}/pause` and `PATCH /watch-queries/{id}/resume` as separate endpoints.
   - What's unclear: These endpoints may use the same `PATCH /watch-queries/{id}` with `{ is_active: false/true }` body (the code shows `update_query` handles `is_active`).
   - Recommendation: Use `PATCH /watch-queries/{id}` with `{ is_active: false }` for pause and `{ is_active: true }` for resume, matching the existing backend implementation. No separate pause/resume endpoints exist.

## Sources

### Primary (HIGH confidence)
- Backend source code: `backend/app/api/watch_queries.py`, `backend/app/api/alerts.py`, `backend/app/api/scrapes.py` -- verified exact endpoint signatures, response shapes, SSE event format
- Backend schemas: `backend/app/schemas/watch_query.py`, `backend/app/schemas/alert.py`, `backend/app/schemas/scrape.py` -- verified exact field names and types
- `backend/main.py` -- verified CORS configuration (localhost:5173, localhost:3000)
- npm registry -- verified all package versions on 2026-03-19

### Secondary (MEDIUM confidence)
- [shadcn/ui Vite installation docs](https://ui.shadcn.com/docs/installation/vite) -- `shadcn init -t vite` command
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) -- CSS-first configuration

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all versions verified against npm registry, shadcn/ui Vite template is official
- Architecture: HIGH -- patterns are standard React + TanStack Query; backend API fully read and understood
- Pitfalls: HIGH -- derived from reading actual backend code (SSE event type, CORS config, endpoint shapes)
- API gap finding: HIGH -- verified by reading `GET /watch-queries/` handler which returns `WatchQueryResponse` (no `latest_result`)

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable stack, 30 days)
