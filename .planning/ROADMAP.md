# Roadmap: Price Scraper

## Overview

This roadmap delivers a personal price tracking application in six phases, following the dependency chain: data layer first (everything reads/writes data), scraping engine second (the core value proposition, validated before anything depends on it), API and watch query management third (exposes data and scraping to consumers), scheduling and alerts fourth (automated scraping and threshold detection complete the core loop), frontend dashboard fifth (consumes all backend APIs), and price history visualization plus polish sixth (enhances the drill-down experience and finalizes UX).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 MVP (Phases 1-7) - SHIPPED 2026-03-22</summary>

- [x] **Phase 1: Data Foundation** - SQLAlchemy models, Alembic migrations, repository layer, and SQLite configuration (completed 2026-03-19)
- [x] **Phase 2: Scraping Engine** - Playwright-based scraping with extraction, failure handling, retries, and price history storage (completed 2026-03-19)
- [x] **Phase 3: API + Watch Query Management** - FastAPI REST endpoints for watch query CRUD and on-demand scrape trigger
- [x] **Phase 4: Scheduling + Alerts** - APScheduler background jobs and threshold-based alert system with SSE notifications
- [x] **Phase 5: Dashboard Frontend** - React dashboard with query cards, drill-down views, and visual indicators
- [x] **Phase 6: Price History Visualization + Polish** - Price history charts, tables, time filtering, and dark mode
- [x] **Phase 7: Advanced Alert Enhancements** - Percentage-based price drop alerts, all-time low badge on QueryCard, and alert cooldown to prevent threshold spam (completed 2026-03-22)

</details>

### Milestone v1.1: Scraping & Data Quality

- [ ] **Phase 8: Scrape Health Dashboard** - Per-URL health tracking with success rates, failure visibility, and status indicators on dashboard cards
- [ ] **Phase 9: Wayback Price Comparisons** - Contextual price-ago stats, rolling averages, and good deal indicators alongside price history
- [ ] **Phase 10: Multi-Product Fuzzy Matching** - RapidFuzz-based cross-retailer product grouping with user confirmation workflow
- [ ] **Phase 11: Polish & P2 Features** - Health sparklines, stale URL detection, match group best-price highlight, and price percentile ranking

## Phase Details

<details>
<summary>v1.0 MVP Phase Details (Phases 1-7)</summary>

### Phase 1: Data Foundation
**Goal**: A working data layer that all subsequent phases can read from and write to, with migration tooling from day one
**Depends on**: Nothing (first phase)
**Requirements**: None directly (foundational infrastructure that enables all 24 requirements)
**Success Criteria** (what must be TRUE):
  1. SQLAlchemy models exist for all six tables (watch_queries, retailer_urls, scrape_results, alerts, scrape_jobs, app_settings) and can be created via Alembic migration
  2. Repository functions can create, read, update, and delete watch queries and their associated retailer URLs against a live SQLite database
  3. SQLite is configured with WAL mode and busy_timeout on every connection (verified by querying PRAGMA values)
  4. Prices are stored as integer cents throughout the data layer (no floating-point price values anywhere)
**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md — Project scaffold, all six SQLAlchemy models, Alembic setup, and initial migration
- [x] 01-02-PLAN.md — Repository layer (watch query CRUD), Pydantic schemas, and repository tests
- [x] 01-03-PLAN.md — SQLite PRAGMA verification tests and migration smoke tests

### Phase 2: Scraping Engine
**Goal**: The scraper can fetch a retailer page, extract product data, store results as historical records, and handle failures gracefully -- validated via CLI before any API exists
**Depends on**: Phase 1
**Requirements**: SCRAPE-01, SCRAPE-04, HIST-01, HIST-02
**Success Criteria** (what must be TRUE):
  1. Running a scrape against a retailer URL extracts product name, current price, retailer name, and listing URL using Playwright headless browser
  2. Every scrape result is persisted as an immutable record with product name, retailer name, price (integer cents), listing URL, and timestamp
  3. Price delta (higher/lower/unchanged) and percentage change are calculated correctly against the previous scrape result for the same listing
  4. A failed scrape retries 2-3 times with exponential backoff and stores an error status with failure reason
  5. A CLI test script can execute a scrape end-to-end without needing the API or frontend
**Plans:** 3/3 plans complete

Plans:
- [x] 02-01-PLAN.md — Base extractor contracts, registry, browser manager, and 5 retailer extractors with mock HTML tests
- [x] 02-02-PLAN.md — Scrape service orchestration, retry logic with tenacity, ScrapeResult/ScrapeJob repository
- [x] 02-03-PLAN.md — Price delta calculation and CLI validation script (print-only, no DB)

### Phase 3: API + Watch Query Management
**Goal**: Users can manage watch queries through REST endpoints and trigger on-demand scrapes, with all CRUD operations validated
**Depends on**: Phase 2
**Requirements**: QUERY-01, QUERY-02, QUERY-03, QUERY-04, QUERY-05, SCRAPE-03
**Success Criteria** (what must be TRUE):
  1. User can create a watch query via API with a search term, one or more retailer URLs, and a price threshold
  2. User can edit a watch query's name, threshold, and retailer URLs; and the system filters duplicate URLs at create and edit time
  3. User can delete a watch query and pause/resume it (paused queries retain configuration)
  4. User can trigger an on-demand scrape for any watch query via API and the scrape executes using the Phase 2 engine
  5. All endpoints return proper Pydantic-validated responses with appropriate HTTP status codes
**Plans:** 3/3 plans complete

Plans:
- [x] 03-01-PLAN.md — FastAPI app skeleton with CORS, router mounting, POST create endpoint, and test infrastructure (Wave 0)
- [x] 03-02-PLAN.md — Watch query CRUD endpoints (GET list, GET detail with embedded results, PATCH with URL dedup, DELETE, pause/resume)
- [x] 03-03-PLAN.md — On-demand scrape trigger endpoint and price history endpoint with computed deltas

### Phase 4: Scheduling + Alerts
**Goal**: Scrapes run automatically on user-configured schedules and alerts fire when prices drop to or below threshold -- completing the end-to-end value loop without manual intervention
**Depends on**: Phase 3
**Requirements**: SCRAPE-02, ALERT-01, ALERT-02, ALERT-03, ALERT-04
**Success Criteria** (what must be TRUE):
  1. Scraping runs automatically on a per-query configurable schedule (every 6h, 12h, daily, or weekly) as a background job that executes even when the user is not actively using the app
  2. An alert record is created when a scraped price is at or below the watch query's configured threshold
  3. Connected browser clients receive real-time notification via SSE when a new alert fires (badge count and toast)
  4. User can view an alert log showing all triggered alerts with query name, product name, price, retailer, and timestamp
  5. User can mark individual alerts as read and dismiss all alerts; badge count reflects unread only
**Plans:** 3/3 plans complete

Plans:
- [x] 04-01-PLAN.md — APScheduler singleton, alert evaluation service with re-breach detection, alert repository, and lifespan/route integration
- [x] 04-02-PLAN.md — Alert CRUD endpoints (list, mark read, dismiss all, unread count)
- [x] 04-03-PLAN.md — SSE stream endpoint for real-time alert push to browser clients

### Phase 5: Dashboard Frontend
**Goal**: Users interact with the application through a browser-based dashboard showing all watch queries, their status, and drill-down details
**Depends on**: Phase 4
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, UI-01
**Success Criteria** (what must be TRUE):
  1. Dashboard displays all active watch queries with query name, lowest current price across retailers, last scrape timestamp, and scrape status indicator (success/error/running/paused)
  2. Queries with at least one listing at or below threshold are visually highlighted with a color or badge
  3. User can drill down into a watch query to see all matched listings, current prices, price deltas, and navigate to price history
  4. Within a watch query's results, the listing with the lowest current price is highlighted across retailer URLs
  5. Watch query CRUD forms (create, edit, pause, delete) are functional in the UI
**Plans:** 4/4 plans complete

Plans:
- [x] 05-01-PLAN.md — React + Vite + shadcn/ui scaffold, TypeScript types, API client, TanStack Query hooks, layout shell
- [x] 05-02-PLAN.md — Dashboard page with query card grid, status indicators, threshold highlighting
- [x] 05-03-PLAN.md — Drill-down slide-over with listing details, CRUD form dialogs, delete confirmation
- [x] 05-04-PLAN.md — Alert bell dropdown, SSE toast hook, alert log page, final dashboard wiring

### Phase 6: Price History Visualization + Polish
**Goal**: Users can explore detailed price history through interactive charts and tables, and the application has a polished visual experience with dark mode
**Depends on**: Phase 5
**Requirements**: HIST-03, HIST-04, HIST-05, UI-02
**Success Criteria** (what must be TRUE):
  1. Price history for a listing is displayed as a line chart with a horizontal dashed threshold line overlay
  2. Price history for a listing is displayed as a sortable table with date, price, and delta columns (default: newest first)
  3. User can filter the price history chart and table by time range (7d, 30d, 90d, all)
  4. Application supports dark mode toggle and renders correctly in both light and dark themes
**Plans:** 2/2 plans complete

Plans:
- [x] 06-01-PLAN.md — Price history chart, sortable table, time range filtering, and QuerySheet/ListingRow wiring
- [x] 06-02-PLAN.md — Dark mode with Tailwind CSS v4 @custom-variant, next-themes ThemeProvider, and ThemeToggle

### Phase 7: Advanced Alert Enhancements
**Goal**: Alerting becomes smarter and less spammy — users get notified on meaningful price drops (percentage-based), see at a glance when a price is an all-time low, and aren't bombarded by repeated alerts when a price oscillates around a threshold
**Depends on**: Phase 6
**Requirements**: ALERT-05, ALERT-06, ALERT-07
**Success Criteria** (what must be TRUE):
  1. A configurable percentage drop alert fires when a scraped price is X% below the rolling 30-day average for that listing (configurable per watch query, stored alongside the absolute threshold)
  2. QueryCard displays an "all-time low" badge when the current lowest price across all retailers for that watch query is the lowest price ever recorded in scrape_results for that query
  3. Alert cooldown prevents a new alert from firing within a configurable time window (default 24h) after the last alert for the same watch query; the cooldown period is configurable per watch query
**Plans:** 3/3 plans complete

Plans:
- [x] 07-01-PLAN.md — Alembic migration, model/schema/repo extensions, alert service cooldown + pct drop logic with tests
- [x] 07-02-PLAN.md — API endpoint wiring for new fields, is_all_time_low computation on detail endpoint
- [x] 07-03-PLAN.md — Frontend TypeScript types, All-Time Low badge on QueryCard, form fields for pct drop and cooldown

</details>

### Phase 8: Scrape Health Dashboard
**Goal**: Users can see at a glance which retailer URLs are healthy, degraded, or failing -- and every scrape attempt is tracked so no failure goes unnoticed
**Depends on**: Phase 7
**Requirements**: HEALTH-01, HEALTH-02, HEALTH-03, HEALTH-04
**Success Criteria** (what must be TRUE):
  1. User can navigate to a scrape health page that lists every retailer URL with its success rate (computed over last N attempts, not calendar windows), last successful scrape timestamp, consecutive failure count, and last error type
  2. Each URL is visually categorized as healthy (green), degraded (yellow), or failing (red) based on its recent scrape outcomes, with thresholds clearly applied
  3. User can sort the health URL list by status, watch query, and last success date, and filter to show only degraded or failing URLs
  4. Dashboard query cards display a health status indicator for each URL so the user can spot problems without navigating to the health page
**Plans:** 3/3 plans complete

Plans:
- [x] 08-01-PLAN.md — Backend data model, migration, repository, scrape service integration, and health API endpoint
- [x] 08-02-PLAN.md — Frontend health page with table, sort/filter, status dots, routing, and nav link
- [x] 08-03-PLAN.md — QueryCard per-URL health mini-dots integration

### Phase 9: Wayback Price Comparisons
**Goal**: Users see contextual price history alongside current prices -- how much a product cost 30 and 90 days ago, whether the current price is a good deal relative to historical averages, and the all-time high price
**Depends on**: Phase 8
**Requirements**: WAYBACK-01, WAYBACK-02, WAYBACK-03, WAYBACK-04
**Success Criteria** (what must be TRUE):
  1. Watch query detail view shows the price 30 days ago and 90 days ago for each listing, with the actual comparison date displayed alongside the period label (e.g., "30d ago: $45.99 on Mar 12")
  2. Watch query detail view shows 30-day and 90-day rolling average prices with sample counts displayed; averages are suppressed (not shown) when fewer than 3 data points exist in the window
  3. Each listing shows a good deal / bad deal indicator based on whether the current price is below the 90-day rolling average
  4. The all-time high price is displayed alongside the existing all-time low for each listing
**Plans:** 0/2 plans executed

Plans:
- [ ] 09-01-PLAN.md — Backend repo functions (nearest-date price lookup, per-URL all-time extremes), schema extension, detail endpoint wiring
- [ ] 09-02-PLAN.md — Frontend TypeScript types, formatShortDate, WaybackStats/DealBadge in ListingRow, visual verification

### Phase 10: Multi-Product Fuzzy Matching
**Goal**: The system automatically detects when different retailer URLs sell the same product and groups them so the user can compare prices across retailers for a single item
**Depends on**: Phase 9
**Requirements**: MATCH-01, MATCH-02, MATCH-03, MATCH-04
**Success Criteria** (what must be TRUE):
  1. After a scrape completes, a background job runs fuzzy title matching (using RapidFuzz) to detect product matches across retailer URLs without blocking the scrape pipeline
  2. User can review match suggestions and confirm or reject each group; confirmed and rejected decisions persist across future matching runs
  3. User can view confirmed match groups showing matched listings side-by-side with current prices, last scrape timestamps, and links to each listing's price history
  4. Title normalization (lowercasing, noise token removal, whitespace collapsing) is applied before matching to reduce false positives from retailer-specific title formatting
**Plans**: TBD

Plans:
- [ ] 10-01-PLAN.md — TBD
- [ ] 10-02-PLAN.md — TBD
- [ ] 10-03-PLAN.md — TBD

### Phase 11: Polish & P2 Features
**Goal**: The health dashboard and match group views get visual enhancements that make data easier to scan at a glance -- sparklines, staleness warnings, best-price highlights, and price percentile context
**Depends on**: Phase 10
**Requirements**: POLISH-01, POLISH-02, POLISH-03, POLISH-04
**Success Criteria** (what must be TRUE):
  1. Scrape health dashboard shows a sparkline of success rate over time for each retailer URL (using existing Recharts)
  2. Health dashboard flags URLs that have not had a successful scrape within a configurable staleness window, with suggested actions (remove, retry, investigate)
  3. In a confirmed match group, the retailer URL with the current lowest price is visually highlighted
  4. Each listing in the price history view shows the current price's percentile rank within its own scrape history (e.g., "cheaper than 85% of recorded prices")
**Plans**: TBD

Plans:
- [ ] 11-01-PLAN.md — TBD
- [ ] 11-02-PLAN.md — TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 3/3 | Complete | 2026-03-19 |
| 2. Scraping Engine | v1.0 | 3/3 | Complete | 2026-03-19 |
| 3. API + Watch Query Management | v1.0 | 3/3 | Complete | - |
| 4. Scheduling + Alerts | v1.0 | 3/3 | Complete | - |
| 5. Dashboard Frontend | v1.0 | 4/4 | Complete | - |
| 6. Price History Visualization + Polish | v1.0 | 2/2 | Complete | - |
| 7. Advanced Alert Enhancements | v1.0 | 3/3 | Complete | 2026-03-22 |
| 8. Scrape Health Dashboard | v1.1 | 3/3 | Complete   | 2026-03-23 |
| 9. Wayback Price Comparisons | v1.1 | 0/2 | Planned    |  |
| 10. Multi-Product Fuzzy Matching | v1.1 | 0/3 | Not started | - |
| 11. Polish & P2 Features | v1.1 | 0/2 | Not started | - |
