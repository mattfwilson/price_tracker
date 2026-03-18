# Price Scraper

## What This Is

A personal full-stack web application that scrapes product prices from user-specified retailer websites (Amazon, BestBuy, Walmart, etc.), stores historical price data over time, and alerts the user when prices drop below configurable thresholds. It runs locally as a background service with a browser-based dashboard.

## Core Value

The full loop must work: a scheduled scrape runs automatically, finds a price at or below the configured threshold, and triggers a visible alert — end-to-end without manual intervention.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can create watch queries with a search term, one or more retailer URLs, and a price threshold
- [ ] User can edit, pause, and delete watch queries
- [ ] Scraper fetches product name, current price, and direct listing URL from each retailer using Playwright (headless browser)
- [ ] Scraping runs on a user-configured schedule (e.g., every 6 hours, daily, weekly) as a background job via APScheduler
- [ ] User can trigger an on-demand scrape for any watch query from the UI
- [ ] Scraping failures are handled gracefully with retry logic and error status visible in the UI
- [ ] Every scrape result is stored with: product name, retailer, price, listing URL, and timestamp
- [ ] Price delta is calculated and displayed (↑ higher / ↓ lower / — unchanged) vs. previous scrape
- [ ] Price history is displayed per listing in a sortable table and a simple line chart
- [ ] Alerts fire when a scraped price is at or below the watch query's threshold
- [ ] In-app notification badge/toast surfaces triggered alerts
- [ ] All triggered alerts are logged and viewable
- [ ] Dashboard shows all active watch queries with their latest results at a glance
- [ ] Drill-down view per watch query shows all matched listings, current prices, deltas, and price history
- [ ] Visual indicators highlight listings below threshold and show price direction

### Out of Scope

- User authentication / multi-user support — personal tool, single user only
- Email or push notifications — stretch goal, not v1
- Mobile app — web-first

## Context

- Personal tool, runs on local machine and accessed via localhost
- Python backend (FastAPI) + React frontend
- SQLite for storage (file-based, zero setup)
- Playwright for headless browser automation (needed for dynamic retailer pages)
- APScheduler for background job scheduling
- Project structure: scraping service / data layer / API layer / frontend UI — clear separation
- Must include a README with setup instructions and guidance for adding new retailer targets

## Constraints

- **Stack**: Python (FastAPI) backend, React frontend — no switching mid-project
- **Database**: SQLite — no external database server required
- **Scraping**: Playwright only — retailers render dynamically, static HTTP scraping won't work
- **Scheduling**: APScheduler — embedded in the Python process, no external queue service needed
- **Deployment**: Local machine only — no cloud deployment concerns for v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SQLite over PostgreSQL | Personal/local use, zero setup friction | — Pending |
| Python backend over Node.js | Strong scraping/scheduling ecosystem, Playwright has excellent Python bindings | — Pending |
| APScheduler over Celery/Redis | Lightweight, embedded, no broker needed for single-user local app | — Pending |
| Playwright over Puppeteer | Python-native, better async support, handles dynamic retailer pages | — Pending |

---
*Last updated: 2026-03-18 after initialization*
