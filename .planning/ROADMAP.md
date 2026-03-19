# Roadmap: Price Scraper

## Overview

This roadmap delivers a personal price tracking application in six phases, following the dependency chain: data layer first (everything reads/writes data), scraping engine second (the core value proposition, validated before anything depends on it), API and watch query management third (exposes data and scraping to consumers), scheduling and alerts fourth (automated scraping and threshold detection complete the core loop), frontend dashboard fifth (consumes all backend APIs), and price history visualization plus polish sixth (enhances the drill-down experience and finalizes UX).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Data Foundation** - SQLAlchemy models, Alembic migrations, repository layer, and SQLite configuration
- [ ] **Phase 2: Scraping Engine** - Playwright-based scraping with extraction, failure handling, retries, and price history storage
- [ ] **Phase 3: API + Watch Query Management** - FastAPI REST endpoints for watch query CRUD and on-demand scrape trigger
- [ ] **Phase 4: Scheduling + Alerts** - APScheduler background jobs and threshold-based alert system with SSE notifications
- [ ] **Phase 5: Dashboard Frontend** - React dashboard with query cards, drill-down views, and visual indicators
- [ ] **Phase 6: Price History Visualization + Polish** - Price history charts, tables, time filtering, and dark mode

## Phase Details

### Phase 1: Data Foundation
**Goal**: A working data layer that all subsequent phases can read from and write to, with migration tooling from day one
**Depends on**: Nothing (first phase)
**Requirements**: None directly (foundational infrastructure that enables all 24 requirements)
**Success Criteria** (what must be TRUE):
  1. SQLAlchemy models exist for all six tables (watch_queries, retailer_urls, scrape_results, alerts, scrape_jobs, app_settings) and can be created via Alembic migration
  2. Repository functions can create, read, update, and delete watch queries and their associated retailer URLs against a live SQLite database
  3. SQLite is configured with WAL mode and busy_timeout on every connection (verified by querying PRAGMA values)
  4. Prices are stored as integer cents throughout the data layer (no floating-point price values anywhere)
**Plans**: TBD

Plans:
- [ ] 01-01: Project scaffold, SQLAlchemy models, and Alembic setup
- [ ] 01-02: Repository layer and Pydantic schemas
- [ ] 01-03: SQLite configuration (WAL mode, busy_timeout) and data layer validation

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
**Plans**: TBD

Plans:
- [ ] 02-01: Playwright browser manager and base extractor with Amazon implementation
- [ ] 02-02: Scraping service, retry logic, and error handling
- [ ] 02-03: Price history storage, delta calculation, and CLI validation script

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
**Plans**: TBD

Plans:
- [ ] 03-01: FastAPI app skeleton with lifespan and CORS configuration
- [ ] 03-02: Watch query CRUD endpoints with duplicate URL filtering
- [ ] 03-03: On-demand scrape endpoint and scrape results/history endpoints

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
**Plans**: TBD

Plans:
- [ ] 04-01: APScheduler integration with FastAPI lifespan and per-query job management
- [ ] 04-02: Alert evaluation service and alert CRUD endpoints
- [ ] 04-03: SSE EventManager for real-time alert push to browser clients

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
**Plans**: TBD

Plans:
- [ ] 05-01: React + Vite + TypeScript scaffold with API client and TanStack Query setup
- [ ] 05-02: Dashboard view with query cards, status indicators, and threshold highlighting
- [ ] 05-03: Watch query CRUD forms and drill-down view with listing details
- [ ] 05-04: Alert notification badge, toast, and alert log view with SSE integration

### Phase 6: Price History Visualization + Polish
**Goal**: Users can explore detailed price history through interactive charts and tables, and the application has a polished visual experience with dark mode
**Depends on**: Phase 5
**Requirements**: HIST-03, HIST-04, HIST-05, UI-02
**Success Criteria** (what must be TRUE):
  1. Price history for a listing is displayed as a line chart with a horizontal dashed threshold line overlay
  2. Price history for a listing is displayed as a sortable table with date, price, and delta columns (default: newest first)
  3. User can filter the price history chart and table by time range (7d, 30d, 90d, all)
  4. Application supports dark mode toggle and renders correctly in both light and dark themes
**Plans**: TBD

Plans:
- [ ] 06-01: Price history line chart with threshold overlay (Recharts)
- [ ] 06-02: Price history sortable table with time range filtering
- [ ] 06-03: Dark mode implementation with Tailwind CSS

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 0/3 | Not started | - |
| 2. Scraping Engine | 0/3 | Not started | - |
| 3. API + Watch Query Management | 0/3 | Not started | - |
| 4. Scheduling + Alerts | 0/3 | Not started | - |
| 5. Dashboard Frontend | 0/4 | Not started | - |
| 6. Price History Visualization + Polish | 0/3 | Not started | - |
