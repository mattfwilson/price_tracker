# Price Scraper

## What This Is

A personal full-stack web application that scrapes product prices from user-specified retailer websites (Amazon, BestBuy, Walmart, etc.), stores historical price data over time, and alerts the user when prices drop below configurable thresholds. It runs locally as a background service with a browser-based dashboard.

## Core Value

The full loop must work: a scheduled scrape runs automatically, finds a price at or below the configured threshold, and triggers a visible alert — end-to-end without manual intervention.

## Current Milestone: v1.1 Scraping & Data Quality

**Goal:** Make the scraper smarter, more observable, and better at surfacing price context.

**Target features:**
- Scrape health dashboard — per-URL error rates, last success timestamps, failure visibility
- Wayback price comparison — contextual "X days ago: $Y" stats alongside price history
- Multi-product matching — fuzzy title matching to surface cross-retailer deals on the same item

## Requirements

### Validated

- ✓ User can create, edit, pause, and delete watch queries — v1.0 Phase 3
- ✓ Scraper fetches product name, current price, and listing URL via Playwright headless browser — v1.0 Phase 2
- ✓ Scraping runs on a per-query configurable schedule as a background job via APScheduler — v1.0 Phase 4
- ✓ User can trigger an on-demand scrape from the UI — v1.0 Phase 3
- ✓ Scraping failures handled gracefully with retry logic and error status visible in UI — v1.0 Phase 2
- ✓ Every scrape result stored with product name, retailer, price, listing URL, and timestamp — v1.0 Phase 2
- ✓ Price delta calculated and displayed vs. previous scrape — v1.0 Phase 2
- ✓ Price history displayed per listing in sortable table and line chart with time range filtering — v1.0 Phase 6
- ✓ Alerts fire when price is at or below threshold, with in-app badge/toast and alert log — v1.0 Phase 4
- ✓ Dashboard shows all watch queries with latest results, threshold highlighting, and drill-down view — v1.0 Phase 5
- ✓ Percentage-based drop alerts, all-time low badge, and configurable alert cooldown — v1.0 Phase 7

### Active

- [ ] User can view a scrape health dashboard showing per-URL success rate, last successful scrape, and consecutive failure count
- [ ] URLs with repeated failures are visually flagged so the user can investigate or remove them
- [ ] User can see contextual price comparisons (e.g., "30 days ago: $X", "90 days ago: $Y") alongside price history
- [ ] Dashboard or detail view surfaces whether the current price is above/below historical averages
- [ ] Scraper detects when multiple retailer URLs resolve to the same product (by fuzzy title match) and groups them as a matched set
- [ ] Matched product groups are surfaced in the UI so the user can compare prices across retailers for the same item

### Out of Scope

- User authentication / multi-user support — personal tool, single user only
- Email or push notifications — deferred to a future milestone
- Mobile app — web-first
- Automatic retailer URL discovery — user still provides URLs explicitly

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

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-22 after v1.1 milestone start*
