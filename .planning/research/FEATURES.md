# Feature Landscape

**Domain:** Personal price tracking / scraping web application
**Researched:** 2026-03-18

## Table Stakes

Features users expect. Missing = product feels incomplete.

### Watch Query Management

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Create watch query with URL + threshold | Core loop; the reason the app exists | Low | User pastes a retailer URL, names the query, sets a target price |
| Edit watch query (threshold, URLs, name) | Users refine thresholds as market prices shift | Low | Inline edit or modal; avoid full-page navigation |
| Delete watch query | Housekeeping; stale queries clutter the dashboard | Low | Soft-delete with undo toast preferred over confirmation dialog |
| Pause/resume watch query | Users travel, want to stop alerts without losing config | Low | Toggle on the query card; paused queries skip scheduled scrapes |
| Multiple URLs per watch query | Same product listed on Amazon, BestBuy, Walmart -- user wants the lowest across all | Medium | Core differentiator of this app vs single-retailer trackers like CamelCamelCamel |
| On-demand scrape trigger | Users want fresh data NOW, not at next schedule | Low | Button per query; must show loading state and result inline |

### Scraping & Data Collection

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Headless browser scraping (Playwright) | Retailers render prices via JS; static HTTP won't work | Medium | Already decided in PROJECT.md; Playwright is the right call |
| Extract product name, price, listing URL | Minimum viable data per scrape | Medium | CSS selector-based extraction; retailers change layouts frequently |
| Scheduled background scraping | The whole point -- unattended monitoring | Medium | APScheduler with configurable intervals (6h, 12h, daily, weekly) |
| Scrape failure handling with retries | Network errors, layout changes, CAPTCHAs -- scrapes WILL fail | Medium | Retry 2-3x with backoff; surface error status in UI, don't silently swallow |
| Store every scrape result with timestamp | Price history requires historical data | Low | Append-only; never overwrite previous results |
| Price delta calculation (up/down/unchanged) | Users need at-a-glance direction, not raw numbers | Low | Compare current vs. previous scrape; display arrow + percentage |

### Price History Display

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Price history line chart per listing | Visual trend is the killer feature of every price tracker (CamelCamelCamel, Keepa) | Medium | Simple line chart with time on X-axis, price on Y-axis; Recharts or Chart.js |
| Price history sortable table | Users want exact numbers, not just visual trends | Low | Date, price, delta columns; sort by date descending by default |
| Threshold line on chart | Shows target price visually against history -- instant "how close am I?" | Low | Horizontal dashed line at threshold; high-value, trivial to implement |
| Time range filter (7d, 30d, 90d, all) | Long histories become unreadable without filtering | Low | Button group above chart; default to 30 days |

### Alert / Notification System

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Alert fires when price <= threshold | The end-to-end value prop: scrape -> detect -> alert | Low | Compare after each scrape; create alert record in DB |
| In-app notification badge + toast | User must SEE the alert without actively checking | Low | Badge count on nav icon; toast on page load if new alerts exist |
| Alert log / history view | Users want to see what triggered and when | Low | Simple list: query name, product, price, retailer, timestamp |
| Mark alert as read/dismissed | Housekeeping; badge count should reflect unread only | Low | Click to dismiss; "mark all read" button |

### Dashboard

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Overview of all active watch queries | Single-screen situational awareness | Medium | Card or table layout showing query name, status, lowest current price, last scrape time |
| Visual indicators for below-threshold | The most important signal must be visually loud | Low | Green highlight, badge, or icon on queries with prices below threshold |
| Last scrape timestamp per query | "Is this data stale?" is always the first question | Low | Relative time ("2 hours ago") with absolute on hover |
| Drill-down view per watch query | Dashboard is summary; users need detail on demand | Medium | Click query -> see all listings, prices, deltas, chart |
| Scrape status indicator (success/error/running) | Users need to know if the system is healthy | Low | Color-coded dot or icon per query |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Sparkline on dashboard cards | At-a-glance trend without drill-down; CamelCamelCamel lacks this on overview | Medium | Tiny inline chart per query on the dashboard; shows 30d trend. High polish, moderate effort |
| Multi-retailer lowest-price comparison | Most trackers are single-retailer; showing "cheapest across all retailers" is genuinely useful | Low | Already have multi-URL per query; just highlight the min price across listings |
| Configurable schedule per query | Different products need different monitoring cadence (flash sales vs stable goods) | Low | Dropdown per query: every 6h, 12h, daily, weekly |
| Price drop percentage display | "Dropped 15% from peak" is more actionable than "$42.50" | Low | Calculate from max historical price; show as badge |
| Export price history (CSV) | Power users want data in spreadsheets | Low | Simple CSV download button on drill-down view |
| Dark mode | Personal tool used at home; many users prefer dark UI | Medium | CSS variables / Tailwind dark mode; do it right from the start or never |
| Scrape selector configuration per retailer | When a retailer changes layout, user can update selectors without code changes | High | UI for editing CSS selectors; preview mode to test. Huge resilience win but complex UX |
| Bulk import watch queries | Setting up 20+ products one-by-one is painful | Low | CSV upload: URL, name, threshold per row |
| Request throttling / rate limit controls | Avoid getting IP-banned by retailers | Medium | Configurable delay between requests, max concurrent scrapes, per-retailer limits |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Multi-user auth system | PROJECT.md explicitly scopes this as single-user personal tool. Auth adds complexity with zero value for the use case | Skip entirely; no login page, no sessions, no user table |
| Email/SMS/push notifications (v1) | Requires SMTP config, external services, credential management -- all friction for a localhost app | In-app alerts only for v1; design alert system so email can be bolted on later (webhook/event pattern) |
| Browser extension | Huge separate codebase, browser store publishing, version maintenance | Web dashboard is sufficient for personal use; extension is a different product |
| Automatic product discovery / recommendations | "Products you might want to track" requires ML, large datasets, user behavior modeling | User manually adds what they care about; that's the correct UX for a personal tool |
| Price prediction / forecasting | Keepa added AI forecasting, but it requires massive historical datasets across millions of products | Show trends and let the human decide; a personal tracker will never have enough data for useful predictions |
| Proxy rotation / IP management | Enterprise scraping concern; a personal tool making a few requests per day won't trigger most rate limits | Respect robots.txt, add reasonable delays, use a single IP. If blocked, the user can investigate per-retailer |
| Mobile app | Separate codebase, deployment pipeline, app store concerns | Responsive web design; the dashboard should work on mobile browsers |
| Real-time websocket price streaming | Massive over-engineering for a tool that scrapes on a schedule | Poll on page load; refresh button for manual update. Scheduled scrapes happen in background |

## Feature Dependencies

```
Store scrape results with timestamp
  -> Price delta calculation (requires previous result to compare)
  -> Price history table (requires historical records)
  -> Price history line chart (requires historical records)
    -> Threshold line on chart (requires chart + threshold data)
    -> Time range filter (requires chart)
    -> Sparkline on dashboard (requires chart component + historical data)

Create watch query with URL + threshold
  -> Scheduled background scraping (requires queries to exist)
    -> Scrape failure handling (requires scraping to run)
  -> On-demand scrape trigger (requires query to exist)
  -> Alert fires when price <= threshold (requires threshold + scrape result)
    -> In-app notification badge + toast (requires alert records)
    -> Alert log / history view (requires alert records)
    -> Mark alert as read/dismissed (requires alert records)

Dashboard overview
  -> Visual indicators for below-threshold (requires dashboard + alert logic)
  -> Drill-down view per query (requires dashboard navigation)
  -> Scrape status indicator (requires scrape job status tracking)

Headless browser scraping (Playwright)
  -> Extract product name, price, listing URL (requires scraping engine)
    -> Scrape selector configuration per retailer (extends extraction logic)
```

## MVP Recommendation

Prioritize (in build order):

1. **Watch query CRUD** -- create, edit, pause, delete. The data model everything else depends on.
2. **Playwright scraping engine** -- extract price, name, URL from a single retailer page. Start with one retailer (Amazon) and get it solid.
3. **Scrape result storage + price delta** -- append-only history, calculate direction.
4. **Scheduled scraping via APScheduler** -- the unattended loop that makes this useful.
5. **Dashboard overview** -- cards for each query with latest price, delta, last scrape time, status.
6. **Price history chart + table** -- line chart with threshold line on drill-down view.
7. **Alert system** -- threshold comparison, in-app badge/toast, alert log.
8. **Multi-retailer support** -- extend scraping to BestBuy, Walmart; highlight lowest price.

Defer:
- **Scrape selector configuration UI**: High complexity, build it after the core loop works. Hardcode selectors per retailer initially and iterate.
- **Export to CSV**: Low effort but low priority; add after core features are solid.
- **Dark mode**: Do it from the start if using Tailwind (cheap), otherwise defer.
- **Bulk import**: Nice-to-have after the single-query flow is polished.

## Sources

- [CamelCamelCamel vs Keepa comparison](https://goaura.com/blog/camelcamelcamel-vs-keepa) - Feature comparison of major price trackers
- [Keepa vs CamelCamelCamel vs Honey (2026)](https://taskmonkey.ai/blog/amazon-price-tracker/keepa-vs-camelcamelcamel-vs-honey) - Multi-tracker feature analysis
- [Best Price Trackers 2026 - Karmanow](https://www.karmanow.com/the-blog/top/the-best-price-trackers) - Market overview of price tracking apps
- [Top Price Monitoring Tools (2026) - Price2Spy](https://www.price2spy.com/blog/top-price-monitoring-tools/) - Enterprise and consumer tool comparison
- [Best Free and Open-Source Price Tracking Tools 2026 - Robotalp](https://robotalp.com/blog/the-best-free-and-open-source-price-stock-tracking-and-alarm-tools-of-2026/) - Open source alternatives
- [PriceGhost - Self-hosted price tracker](https://github.com/clucraft/PriceGhost) - Multi-strategy extraction approach
- [PriceBuddy - Self-hosted tracker](https://github.com/jez500/pricebuddy) - Self-hosted notification patterns
- [Web Scraping Best Practices 2026 - ScrapingBee](https://www.scrapingbee.com/blog/web-scraping-best-practices/) - Rate limiting and anti-detection
- [Web Scraping Challenges 2025 - ScrapingBee](https://www.scrapingbee.com/blog/web-scraping-challenges/) - Current anti-bot landscape
- [Alert and Notification in Web Scraping - Browse AI](https://www.browse.ai/glossary/alert-notification-web-scraping) - Alert system patterns
- [PatternFly Sparkline Chart Guidelines](https://www.patternfly.org/charts/sparkline-chart/design-guidelines/) - Sparkline UX patterns
