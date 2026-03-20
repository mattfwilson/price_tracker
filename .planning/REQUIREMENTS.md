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
- [ ] **HIST-03**: Price history for a listing is displayed as a line chart with a horizontal dashed threshold line overlay
- [ ] **HIST-04**: Price history for a listing is displayed as a sortable table with date, price, and delta columns (default: newest first)
- [ ] **HIST-05**: User can filter the price history chart and table by time range (7d, 30d, 90d, all)

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
- [ ] **UI-02**: Application supports dark mode

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
| HIST-03 | Phase 6 | Pending |
| HIST-04 | Phase 6 | Pending |
| HIST-05 | Phase 6 | Pending |
| ALERT-01 | Phase 4 | Complete |
| ALERT-02 | Phase 4 | Complete |
| ALERT-03 | Phase 4 | Complete |
| ALERT-04 | Phase 4 | Complete |
| DASH-01 | Phase 5 | Complete |
| DASH-02 | Phase 5 | Complete |
| DASH-03 | Phase 5 | Complete |
| DASH-04 | Phase 5 | Complete |
| UI-01 | Phase 5 | Complete |
| UI-02 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-03-18*
*Last updated: 2026-03-18 after roadmap creation*
