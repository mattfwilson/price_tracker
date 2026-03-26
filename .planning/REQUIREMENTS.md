# Requirements: Price Scraper

**Defined:** 2026-03-18
**Core Value:** The full loop must work — a scheduled scrape runs automatically, finds a price at or below the configured threshold, and triggers a visible in-app alert without manual intervention.

## v1 Requirements

### Watch Query Management

- [x] **QUERY-01**: User can create a watch query with a search term, one or more retailer URLs, and a price threshold
- [x] **QUERY-02**: User can edit a watch query's name, price threshold, and retailer URLs
- [x] **QUERY-03**: User can delete a watch query
- [x] **QUERY-04**: User can pause and resume a watch query (paused queries skip scheduled scrapes but retain their config)
- [x] **QUERY-05**: System identifies and filters duplicate retailer URLs within a watch query at creation and edit time

### Scraping

- [x] **SCRAPE-01**: System scrapes retailer pages using Playwright headless browser and extracts product name, current price, retailer name, and direct listing URL per page
- [x] **SCRAPE-02**: Scraping runs automatically on a per-query configurable schedule (every 6h, 12h, daily, or weekly) as a background job — even when the user is not using the app
- [x] **SCRAPE-03**: User can trigger an on-demand scrape for any watch query from the UI
- [x] **SCRAPE-04**: Scraping failures are retried (2–3x with exponential backoff) and error status with failure reason is surfaced in the UI

### Price History

- [x] **HIST-01**: Every scrape result is stored as an immutable historical record: product name, retailer name, price (in integer cents), listing URL, and timestamp
- [x] **HIST-02**: Price delta (↑ higher / ↓ lower / — unchanged) and percentage change are calculated vs. the previous scrape result for each listing
- [x] **HIST-03**: Price history for a listing is displayed as a line chart with a horizontal dashed threshold line overlay
- [x] **HIST-04**: Price history for a listing is displayed as a sortable table with date, price, and delta columns (default: newest first)
- [x] **HIST-05**: User can filter the price history chart and table by time range (7d, 30d, 90d, all)

### Alerts

- [x] **ALERT-01**: System triggers an alert record when a scraped price is at or below the watch query's configured threshold
- [x] **ALERT-02**: In-app notification badge on the nav shows unread alert count; a toast appears when new alerts arrive
- [x] **ALERT-03**: User can view an alert log showing all triggered alerts (query name, product name, price, retailer, timestamp)
- [x] **ALERT-04**: User can mark individual alerts as read and dismiss all alerts at once; badge count reflects unread only

### Dashboard

- [x] **DASH-01**: Dashboard displays all active watch queries with: query name, lowest current price across all retailers, last scrape timestamp, and scrape status
- [x] **DASH-02**: Queries with at least one listing at or below threshold are visually highlighted (color/badge)
- [x] **DASH-03**: User can drill down into a watch query to see all matched listings, current prices, price deltas, and price history chart/table
- [x] **DASH-04**: Each query card shows a scrape status indicator (success / error / running / paused)

### UI

- [x] **UI-01**: Within a watch query's results, the listing with the lowest current price is highlighted across retailer URLs
- [x] **UI-02**: Application supports dark mode

## v1.0 Phase 7 Additions

### Alert Enhancements

- [x] **ALERT-05**: System triggers an alert when a scraped price drops by a configurable percentage (e.g., 10%) below the rolling 30-day average price for that listing — configurable per watch query, evaluated in addition to the absolute threshold check
- [x] **ALERT-06**: QueryCard displays an "all-time low" badge when the current lowest price across all retailers is the lowest price ever recorded for that watch query
- [x] **ALERT-07**: Alert cooldown prevents duplicate alerts from firing within a configurable time window (default 24h) when price fluctuates around a threshold — configurable per watch query

## Milestone v1.1 Requirements

**Defined:** 2026-03-22
**Goal:** Make the scraper smarter, more observable, and better at surfacing price context.

### Scrape Health

- [x] **HEALTH-01**: User can view a health dashboard page listing all retailer URLs with per-URL success rate (last N attempts), last successful scrape timestamp, consecutive failure count, and last error type
- [x] **HEALTH-02**: Retailer URLs are visually categorized as healthy (green), degraded (yellow), or failing (red) based on recent scrape outcomes
- [x] **HEALTH-03**: User can sort and filter the health URL list by status, watch query, and last success date
- [x] **HEALTH-04**: Dashboard query cards show a health status indicator for each URL at a glance

### Wayback Price Comparisons

- [x] **WAYBACK-01**: Watch query detail view shows price 30 days ago and 90 days ago for each listing, with the actual comparison date displayed alongside the label (not just the period label)
- [x] **WAYBACK-02**: Watch query detail view shows 30-day and 90-day rolling average prices with sample counts; averages are suppressed when fewer than 3 data points exist in the window
- [x] **WAYBACK-03**: Each listing shows a good deal / bad deal indicator based on whether the current price is below the 90-day rolling average
- [x] **WAYBACK-04**: Historical all-time high price is displayed alongside the existing all-time low

### Fuzzy Matching

- [ ] **MATCH-01**: System automatically detects when multiple retailer URLs resolve to the same product using fuzzy title matching and groups them as match candidates
- [ ] **MATCH-02**: User can review match suggestions and confirm or reject each group; confirmed and rejected decisions are persisted and respected in future matching runs
- [ ] **MATCH-03**: User can view confirmed match groups showing matched listings side-by-side with current prices, last scrape timestamps, and links to each listing's price history
- [ ] **MATCH-04**: Fuzzy matching runs as a background job after scrape completion and does not block the scrape pipeline

### Polish (P2)

- [ ] **POLISH-01**: Scrape health dashboard shows a sparkline of success rate over time for each retailer URL
- [ ] **POLISH-02**: Health dashboard flags URLs that have not had a successful scrape within a configurable staleness window, with suggested actions (remove, retry, investigate)
- [ ] **POLISH-03**: In a confirmed match group, the retailer URL with the current lowest price is highlighted
- [ ] **POLISH-04**: Each listing in the price history view shows the current price's percentile rank within its own scrape history (e.g., "cheaper than 85% of recorded prices")

## v2 Requirements

### Notifications

- **NOTF-01**: User receives email notification when alert fires
- **NOTF-02**: User can configure notification delivery preferences (in-app only, email, etc.)

### Dashboard Enhancements

- **DASH-05**: Dashboard cards show a sparkline (30-day price trend) per query inline
- **DASH-06**: Price drop percentage from historical peak is displayed per listing

### Data Management

- **DATA-01**: User can export price history for a listing to CSV
- **DATA-02**: User can bulk import watch queries via CSV upload (search term, retailer URLs, threshold per row)

### Scraping Resilience

- **SCRAPE-05**: User can configure CSS selectors per retailer via a UI (no code changes needed when layouts change)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-user authentication | Personal/single-user tool — auth adds complexity with zero value |
| Browser extension | Separate codebase and distribution; web dashboard is sufficient |
| Mobile app | Responsive web design covers mobile browsers |
| Price prediction / AI forecasting | Requires massive datasets; personal tracker will never have enough data |
| Proxy rotation / IP management | Enterprise concern; personal tool making a few requests/day won't trigger rate limits |
| Real-time WebSocket price streaming | Over-engineering for a scheduled scraping tool |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| QUERY-01 | Phase 3 | Complete |
| QUERY-02 | Phase 3 | Complete |
| QUERY-03 | Phase 3 | Complete |
| QUERY-04 | Phase 3 | Complete |
| QUERY-05 | Phase 3 | Complete |
| SCRAPE-01 | Phase 2 | Complete |
| SCRAPE-02 | Phase 4 | Complete |
| SCRAPE-03 | Phase 3 | Complete |
| SCRAPE-04 | Phase 2 | Complete |
| HIST-01 | Phase 2 | Complete |
| HIST-02 | Phase 2 | Complete |
| HIST-03 | Phase 6 | Complete |
| HIST-04 | Phase 6 | Complete |
| HIST-05 | Phase 6 | Complete |
| ALERT-01 | Phase 4 | Complete |
| ALERT-02 | Phase 4 | Complete |
| ALERT-03 | Phase 4 | Complete |
| ALERT-04 | Phase 4 | Complete |
| DASH-01 | Phase 5 | Complete |
| DASH-02 | Phase 5 | Complete |
| DASH-03 | Phase 5 | Complete |
| DASH-04 | Phase 5 | Complete |
| UI-01 | Phase 5 | Complete |
| UI-02 | Phase 6 | Complete |
| ALERT-05 | Phase 7 | Complete |
| ALERT-06 | Phase 7 | Complete |
| ALERT-07 | Phase 7 | Complete |
| HEALTH-01 | Phase 8 | Complete |
| HEALTH-02 | Phase 8 | Complete |
| HEALTH-03 | Phase 8 | Complete |
| HEALTH-04 | Phase 8 | Complete |
| WAYBACK-01 | Phase 9 | Complete |
| WAYBACK-02 | Phase 9 | Complete |
| WAYBACK-03 | Phase 9 | Complete |
| WAYBACK-04 | Phase 9 | Complete |
| MATCH-01 | Phase 10 | Pending |
| MATCH-02 | Phase 10 | Pending |
| MATCH-03 | Phase 10 | Pending |
| MATCH-04 | Phase 10 | Pending |
| POLISH-01 | Phase 11 | Pending |
| POLISH-02 | Phase 11 | Pending |
| POLISH-03 | Phase 11 | Pending |
| POLISH-04 | Phase 11 | Pending |

**Coverage:**
- v1.0 requirements: 27 total — all complete
- v1.1 requirements: 16 total (Phases 8–11)
- Mapped to phases: 43
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-22 after v1.1 milestone start*
