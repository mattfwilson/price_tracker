# Phase 5: Dashboard Frontend - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

A browser-based React dashboard that consumes all backend APIs from Phases 1-4. Users see watch query cards, drill into listing details, manage queries via CRUD forms, and receive real-time alert notifications via SSE. Price history charts/tables and dark mode are Phase 6 — out of scope here.

</domain>

<decisions>
## Implementation Decisions

### Navigation structure
- Two routes: `/` (dashboard) and `/alerts` (alert log page)
- Drill-down opens as a **slide-over panel** on top of the dashboard (no route change)
- React Router required for the two routes
- **Header:** Minimal — app name ("Price Scraper") on the left, notification bell with unread badge count on the right. No sidebar.
- **Bell icon behavior:** Clicking opens a dropdown panel inline (not navigate to /alerts). Dropdown has a "View all" link that routes to /alerts.

### Query card design
- **Layout:** Responsive card grid — 2-3 columns on desktop, 1 column on mobile
- **Card content:**
  - Query name (top left)
  - URL count ("3 urls", top right)
  - Three-dot menu (⋯, top right corner) — opens dropdown with: Edit, Pause/Resume, Scrape Now, Delete
  - Lowest current price across all retailers + delta direction arrow (↑↓—)
  - Threshold value ("Threshold: $400")
  - Status dot + label (● OK / ● Error / ● Running / ⊘ Paused) + last scrape timestamp
- **Threshold-breached highlight:** Green border (thick, left or outline) + small "[ALERT]" or "Below threshold" badge near the price (DASH-02)
- **Card click (body):** Opens the drill-down slide-over
- **⋯ menu actions:** Edit (opens create/edit modal pre-filled), Pause/Resume (toggle), Scrape Now (trigger on-demand), Delete (opens confirm dialog)
- **"+ New Query" card:** Last card in the grid acts as an add button

### Drill-down slide-over
- Slide-over header: query name, threshold, status indicator
- Each retailer URL shown as a row: product name, current price, delta direction
- Lowest-price listing gets a "Lowest" badge (UI-01)
- "View history" link per listing — **disabled/greyed out in Phase 5** (Phase 6 activates it)
- No "Scrape Now" button in the slide-over; that action is in the ⋯ menu on the card

### CRUD form UX
- Create and Edit use the **same modal dialog** (centered overlay), pre-filled with existing values for edit
- **Form fields:** Name (text), Threshold (dollar amount input — frontend converts to cents before sending to API; e.g., "$400" → 40000), Schedule (dropdown: daily / weekly / every 6h / every 12h), URLs (dynamic list with "+ Add URL" button)
- **Deduplication:** Backend handles silently; frontend shows the returned clean list
- **Delete confirmation:** Simple dialog — "Delete [query name]? This cannot be undone." with Cancel and Delete buttons. No type-to-confirm.

### Alert notification UX
- **Bell dropdown panel** (opens on click, closes on outside-click or re-click):
  - Header: "Alerts (N unread)"
  - Lists 5-10 most recent alerts: unread dot, query name, price, retailer, relative time
  - Clicking an alert marks it as read (PATCH /alerts/{id}/read)
  - Footer: "Dismiss all" button + "View all" link to /alerts
- **Toast notifications** (from SSE stream):
  - Bottom-right corner
  - Content: query name, price, retailer, "Below threshold!"
  - Auto-dismiss after 5 seconds; manual [x] close
  - Badge count in header updates in real-time from SSE unread_count field (no separate fetch needed)
- **Alert log page (/alerts):**
  - Table layout, newest first
  - Columns: unread dot, query name, product name, price, retailer, timestamp
  - "Dismiss all" button top-right (ALERT-04)
  - Clicking a row marks it as read

### Claude's Discretion
- Exact Tailwind class choices, spacing, typography
- Whether to use a headless UI library (Radix, Headless UI) or build primitives from scratch
- TanStack Query cache invalidation strategy (refetch vs optimistic update)
- SSE reconnect/error handling strategy
- Loading skeletons vs spinner during data fetch
- Error state handling (API errors, network errors)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — DASH-01 through DASH-04 (dashboard view requirements), UI-01 (lowest-price highlight), ALERT-02 (badge + toast), ALERT-03 (alert log view), ALERT-04 (mark read / dismiss all)
- `.planning/PROJECT.md` — Stack constraints (React frontend, FastAPI backend, local-only), out-of-scope (auth, email notifications)

### Backend API contracts (Phase 4 output)
- `.planning/phases/04-scheduling-alerts/04-CONTEXT.md` — SSE event payload shape (alert_id, watch_query_id, watch_query_name, product_name, price_cents, retailer_name, listing_url, created_at, unread_count), alert CRUD endpoint behavior
- `.planning/phases/03-api-watch-query-management/03-CONTEXT.md` — Watch query CRUD endpoint shape, on-demand scrape response, price history endpoint, CORS locked to localhost:5173

### Prior phase context
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — Prices stored as integer cents throughout; frontend must display as dollars ($X.XX)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/schemas/watch_query.py` — `WatchQueryDetailResponse` (id, name, threshold_cents, is_active, schedule, retailer_urls[].latest_result) — this is what the list/detail endpoints return; frontend types should mirror this
- `backend/app/schemas/alert.py` — `AlertResponse` (id, watch_query_id, watch_query_name, product_name, price_cents, retailer_name, listing_url, is_read, created_at) and `AlertSSEPayload` (same + unread_count) — SSE events carry full data, no follow-up fetch needed
- `backend/app/api/alerts.py` — SSE endpoint at `GET /alerts/stream`, event type `"alert"`, 30s keepalive `: keepalive` comment

### Established Patterns
- Backend CORS locked to `http://localhost:5173` (Vite dev default) and `http://localhost:3000` — frontend must run on one of these
- All prices in the API are **integer cents** — frontend converts for display (price_cents / 100 → "$X.XX")
- Delta direction field: `"new" | "higher" | "lower" | "unchanged"` — map to ↑ ↓ — symbols

### Integration Points
- `GET /watch-queries/` → dashboard card list (use `WatchQueryDetailResponse` for embedded latest_result)
- `GET /watch-queries/{id}` → drill-down slide-over data
- `POST /watch-queries/` → create form submit
- `PATCH /watch-queries/{id}` → edit form submit
- `DELETE /watch-queries/{id}` → delete confirm
- `PATCH /watch-queries/{id}/pause` and `/resume` → pause/resume toggle
- `POST /watch-queries/{id}/scrape` → Scrape Now action
- `GET /alerts/` → alert log table and bell dropdown
- `GET /alerts/unread-count` → initial badge count on load
- `PATCH /alerts/{id}/read` → mark individual alert read
- `POST /alerts/dismiss-all` → dismiss all button
- `GET /alerts/stream` → SSE for real-time toast + badge update

</code_context>

<specifics>
## Specific Ideas

- No specific references or "I want it like X" moments — open to standard clean approaches for visual execution

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-dashboard-frontend*
*Context gathered: 2026-03-19*
