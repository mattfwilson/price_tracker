# Project Research Summary

**Project:** Price Tracker v1.1
**Domain:** Scrape health monitoring, wayback price comparisons, multi-product fuzzy matching
**Researched:** 2026-03-22
**Confidence:** HIGH

## Executive Summary

Price Tracker v1.1 extends a working v1.0 foundation with three independent features that each address a real operational gap. The codebase already has everything needed for two of the three features: scrape health metrics can be derived from existing `ScrapeJob` and `ScrapeResult` data with only a new `scrape_attempts` table added; wayback price comparisons require zero schema changes, only new repository queries on `scrape_results`. The third feature — fuzzy product matching — is the only one that adds meaningful new complexity, requiring one new pip dependency (`rapidfuzz`), two new tables, and a background matching service. The overall stack is intentionally minimal: `rapidfuzz>=3.12.0` is the single new dependency and no new frontend npm packages are required.

The recommended build order is health first, wayback second, fuzzy matching third. Health must come first because the `scrape_attempts` schema migration activates per-URL tracking for all future scrapes — every day without it is lost observability data. Wayback is second because it is pure read-only computation on existing data with no schema changes, making it the lowest-risk feature. Fuzzy matching comes last because it is the most complex feature, benefits from health data to identify URLs with noisy or unreliable product names, and requires the most iterative tuning of any component (matching threshold, title normalization rules). All three integrate cleanly into the existing FastAPI/SQLAlchemy/React layered architecture without requiring new infrastructure.

The primary risks are data quality assumptions that, if unchecked, produce misleading output. Health metrics silently break if built on parsed `error_message` strings rather than structured per-URL attempt records. Wayback comparisons mislead users when sparse scrape history is presented without proximity validation and sample counts. Fuzzy matching produces false positives when raw retailer titles (packed with noise tokens and variant suffixes) are compared without normalization. Each risk has a clear prevention strategy that is build-order-sensitive: the schema migration precedes health metrics, proximity validation precedes wayback UI display, and title normalization precedes any matching logic.

## Key Findings

### Recommended Stack

The v1.0 stack (FastAPI, SQLAlchemy async, Patchright, APScheduler, React 19, TanStack Query 5, Recharts, shadcn/ui) remains unchanged for v1.1. The only addition is `rapidfuzz>=3.12.0` for fuzzy product title matching — MIT license (ruling out `thefuzz`, which is GPL), pre-built C++ wheels for all platforms, and `token_sort_ratio`, `token_set_ratio`, and `cdist` batch operations that are exactly the scorers needed for product title comparison. All three features have been confirmed to require no new frontend npm dependencies: health UI uses the existing `<Table>` and `<Badge>` components, wayback stats are inline text using existing `format.ts` utilities, and match groups use existing `<Card>` components.

Three new database tables are added via a single Alembic migration (all additive, no changes to existing tables): `scrape_attempts` (per-URL scrape outcomes), `product_match_groups` (clustered product groups), and `product_match_members` (group membership with similarity scores). Three composite indexes are recommended for query performance: `scrape_attempts(retailer_url_id, created_at)`, `scrape_results(retailer_url_id, created_at)`, and `scrape_results(created_at)`.

**Core technologies:**
- `rapidfuzz>=3.12.0`: fuzzy product matching — only new dependency, MIT license, C++ core, 16x faster than `thefuzz`
- SQLAlchemy aggregate queries on `scrape_attempts`: health metrics — query-time aggregation, no caching layer needed at personal-tool scale
- Date-windowed SQLAlchemy queries on `scrape_results`: wayback stats — extends the existing `get_rolling_avg_price()` pattern with no new infrastructure
- Alembic migration (single): adds `scrape_attempts`, `product_match_groups`, `product_match_members` — additive only
- APScheduler (existing): debounced background matching job after scrape completion — `max_instances=1`, `coalesce=True`

### Expected Features

**Must have (v1.1 core — P1):**
- Per-URL health status: success rate (last N attempts, not calendar window), last success timestamp, consecutive failure count, error type classification
- Visual health indicators (red/yellow/green) on existing dashboard cards
- Filterable/sortable health URL list at `/health` route
- 30-day and 90-day price-ago comparisons with actual comparison date displayed (not just the label)
- 30-day and 90-day average price with sample count shown alongside
- Historical low/high display extending the existing all-time low badge
- Good deal / bad deal indicator based on 90-day average comparison
- Automatic fuzzy matching with confidence scores using RapidFuzz
- Manual confirm/reject for match suggestions with persistence — mandatory because fuzzy matching always has false positives
- Grouped cross-retailer price comparison view at `/matches` route

**Should have (v1.1 if time permits — P2):**
- Health trend sparklines using existing Recharts installation
- Stale URL auto-detection with suggested actions in health dashboard
- Best-price-across-retailers highlight in match group view (trivial once matching infrastructure exists)
- Price percentile ranking (easy to add once price stats service exists)

**Defer (v2+):**
- Health alerting when a URL degrades (requires notification infrastructure)
- Match group price alerts (requires notification infrastructure)
- Cross-query product matching (significantly higher false positive rate, major complexity increase)
- Automatic URL discovery for matched products (requires search engine scraping or API access)

### Architecture Approach

All three features integrate into the existing single-process layered monolith without structural changes. Each follows the established pattern: Alembic migration, new repository module, new or extended service, new API router or extended endpoint, new frontend page and components wired through TanStack Query. The one cross-cutting integration point is `scrape_service.run_scrape_job()`, which gains a `ScrapeAttempt` write in both the success and failure branches of its per-URL loop — approximately a 10-line change that activates all health tracking. Wayback stats are embedded in the existing `GET /watch-queries/{id}` response (not a separate endpoint per URL) to avoid N+1 frontend requests. Fuzzy matching runs as a debounced background task triggered post-scrape, never in the request path.

**Major components added:**
1. `scrape_attempts` table + `scrape_health` repository + `GET /scrape-health` endpoint + `ScrapeHealthPage` — per-URL operational history and health metric aggregation
2. `get_wayback_stats()` repository function embedded in watch query detail response + `WaybackStats` frontend component — price-at-date and rolling average computation on existing data
3. `match_service.py` background job + `product_match_groups`/`product_match_members` tables + `GET /product-matches` endpoint + `ProductMatchesPage` — RapidFuzz clustering with user confirmation/rejection workflow
4. Modified `scrape_service.run_scrape_job()` — writes `ScrapeAttempt` row per URL per job
5. Modified `QuerySheet` — embeds wayback stats and match indicators in the existing detail view

### Critical Pitfalls

1. **No structured per-URL failure data** — Add `scrape_attempts` table and write a row in both the success and failure branches of `run_scrape_job`. Never parse `ScrapeJob.error_message` strings — the format is unstructured, lossy on failure type, and will silently break.

2. **Calendar-window success rates produce incomparable metrics** — Compute success rate as `successes / total_attempts` scoped to the last N attempts per URL, not over a calendar window. URLs with different scrape schedules must produce comparable rates. Suppress percentage display for fewer than 5 attempts; show "2/3 successful" for small samples instead.

3. **Wayback "30 days ago" showing data from an unrelated date** — Always display the actual comparison date alongside any period label. Enforce a ±3-day proximity window; return null and show "No data" when no scrape falls within it. Show sample count with averages; refuse to compute averages under 3 data points.

4. **Fuzzy matching false positives from retailer title noise** — Normalize before comparing: lowercase, strip known noise tokens (Sponsored, Renewed, Bundle, Refurbished, variant suffixes), collapse whitespace, remove non-alphanumeric except hyphens. Use `token_set_ratio` not raw `ratio`. Start at 85-90% threshold. Require user confirmation for all suggestions; persist confirmed and dismissed pairs.

5. **Fuzzy matching runs in the scrape pipeline and blocks it** — Matching is O(N²). Run as an async background task after scrape completion, never synchronously. Use `cdist` for batch comparison and match only against the latest canonical `product_name` per URL, not all historical title variants.

## Implications for Roadmap

Based on combined research, three primary phases in dependency and risk order:

### Phase 1: Scrape Health Dashboard

**Rationale:** Must come first because the `scrape_attempts` schema migration activates per-URL tracking for all future scrapes. Every day without the migration is lost observability data. Health has zero dependency on the other two features, delivers immediate operational value (which URLs are broken right now), and informs Phase 3 by exposing which URLs have unreliable product names.

**Delivers:** `scrape_attempts` table migration with composite index, `scrape_health` repository (aggregate queries: success rate over last N attempts, last success, consecutive failures, last error type), `GET /scrape-health` API endpoint, `ScrapeHealthPage` at `/health`, `HealthTable` component (sortable, filterable), `HealthBadge` component (green/yellow/red), health indicator dot on existing dashboard cards, `Header` nav link.

**Addresses (from FEATURES.md):** Per-URL health status, visual indicators, filterable URL list, error type classification.

**Avoids (from PITFALLS.md):** Pitfall 1 (parsed error strings), Pitfall 2 (calendar-window rates), Pitfall 6 (stale aggregate queries via composite index).

**Research flag:** Standard patterns — FastAPI route + SQLAlchemy aggregation is well-documented. Skip research-phase.

### Phase 2: Wayback Price Comparisons

**Rationale:** Independent of Phase 1 and Phase 3. Zero schema changes — only new repository query functions and API schema extensions. The lowest-risk and lowest-complexity of the three features. Completing it before fuzzy matching ensures cross-retailer price context is already available when match group views are introduced.

**Delivers:** `get_wayback_stats()` repository function (price at ±3-day proximity window for 7d/30d/90d, rolling averages with sample counts), `WaybackStats` Pydantic schema with actual comparison dates and sample counts, `wayback` field embedded in existing `GET /watch-queries/{id}` response, `WaybackStats` frontend component in `QuerySheet`, good deal/bad deal badge.

**Addresses (from FEATURES.md):** 30d/90d price-ago comparisons, 30d/90d averages, historical low/high display, good deal indicator.

**Avoids (from PITFALLS.md):** Pitfall 3 (stale wayback labels — proximity window and actual date built from day one), misleading averages (sample count in API response, minimum 3-point floor enforced).

**Research flag:** Standard patterns — date-windowed SQL aggregation with an existing precedent in `get_rolling_avg_price()`. Skip research-phase.

### Phase 3: Multi-Product Fuzzy Matching

**Rationale:** Comes last because it is the most complex feature. It benefits from Phase 1 health data (excluding URLs with unreliable product names from matching), has the longest tail (new pip dependency, two new tables, background service, clustering logic, the most frontend surface area), and is the only feature requiring iterative tuning that is best done with real production data already accumulated from Phases 1 and 2.

**Delivers:** `rapidfuzz>=3.12.0` dependency in `pyproject.toml`, `product_match_groups` and `product_match_members` migration, `match_service.py` background job (title normalization pipeline, `cdist` batch comparison, single-linkage clustering at configurable threshold, debounced APScheduler trigger), `GET /product-matches` and `GET /product-matches/{id}` endpoints, `ProductMatchesPage` at `/matches`, `MatchGroupCard` component (cross-retailer price comparison), match indicators in `QuerySheet` and `ListingRow`, confirm/reject workflow with persistence, dismissed pairs excluded from future runs.

**Addresses (from FEATURES.md):** Automatic fuzzy matching with confidence scores, manual confirm/reject, grouped comparison view.

**Avoids (from PITFALLS.md):** Pitfall 4 (false positives — normalization pipeline built and tested before matching logic), Pitfall 5 (quadratic blocking — async background task, `cdist`, debounced).

**Research flag:** Title normalization strategy needs empirical validation. Before writing the normalization pipeline, query 20-30 real `product_name` values from the live database across all 5 supported retailers (Amazon, Walmart, Best Buy, Newegg, Micro Center) and manually test threshold candidates. This is a short spike, not full research-phase, but should precede normalization code.

### Phase 4: Polish and P2 Features

**Rationale:** Best-price-across-retailers highlight, health trend sparklines, and stale URL auto-detection are low-complexity additions that build on Phase 1-3 infrastructure. Group them into a polish phase rather than bloating earlier phases.

**Delivers:** Best-price highlight in `MatchGroupCard`, health trend sparklines using existing Recharts, stale URL flagging with suggested actions in `ScrapeHealthPage`.

**Research flag:** Standard patterns — all additions use already-installed libraries. Skip research-phase.

### Phase Ordering Rationale

- Health first because the `scrape_attempts` migration is time-sensitive — lost tracking data cannot be recovered retroactively.
- Wayback second because it is zero-risk (read-only, no schema changes) and enriches the query detail view that fuzzy matching groups will later reference.
- Fuzzy matching last because it is the only feature requiring empirical tuning with real data, and it has the most integration surface (new page, new background job, modifications to existing views).
- No phase has a hard dependency that blocks parallel work, but this order minimizes rework: health data informs which URLs to exclude from matching, and wayback context enriches match group display.

### Research Flags

Phases needing deeper research during planning:
- **Phase 3 (Fuzzy Matching):** Title normalization strategy — recommend a brief empirical spike reading actual scraped `product_name` values from the live database across all 5 retailers before writing the normalization pipeline. The threshold (85 vs 90) should be confirmed against real data, not guessed.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Health):** FastAPI + SQLAlchemy aggregate queries + indexed table — established pattern, well-documented.
- **Phase 2 (Wayback):** Date-windowed SQL aggregation with an existing precedent in `get_rolling_avg_price()`. No novel patterns.
- **Phase 4 (Polish):** All additions use already-installed libraries (Recharts, shadcn/ui).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing stack validated in v1.0. `rapidfuzz` is the standard production Python fuzzy matching library; MIT license, C++ performance, and `cdist` API confirmed against official documentation. Single new dependency conclusion is high confidence. |
| Features | MEDIUM-HIGH | Table stakes and P1 features well-defined by competitor analysis (CamelCamelCamel, Keepa, ScrapeOps). The exact threshold and normalization rules for fuzzy matching require empirical validation against real scraped titles — that detail is MEDIUM confidence. |
| Architecture | HIGH | Based on direct codebase analysis of existing models, services, repositories, and API patterns. All integration points confirmed in code. No novel architectural patterns required — all three features follow established layer conventions. |
| Pitfalls | HIGH | All critical pitfalls derived from direct codebase analysis plus domain research. The `error_message` concatenation issue is directly observable in current `scrape_service.py`. The O(N²) matching pitfall is a well-documented class of problem with standard prevention strategies. |

**Overall confidence:** HIGH

### Gaps to Address

- **Fuzzy matching threshold:** The 85-90% recommendation is based on general domain guidance, not empirical testing against actual scraped titles in this database. During Phase 3 planning, query real `product_name` values from the live database and manually test threshold candidates before writing matching code.
- **`scrape_attempts` backfill decision:** The Phase 1 migration adds the table with no historical data. The pitfall research recommends a backfill migration that derives past failures from `scrape_jobs` where a URL has no corresponding `scrape_results` row. Decide in Phase 1 planning whether to implement backfill (richer immediate history) or accept that health metrics start fresh from migration date (simpler migration).
- **Wayback proximity window:** The ±3-day proximity window is a recommendation. If the user's scrape schedule is weekly, ±3 days would produce very sparse comparisons. During Phase 2 planning, check the actual scrape frequency distribution in the database and set the window accordingly (reasonable rule: proximity window = 2× scrape interval).
- **Match confirmation UX flow:** The research confirms that human-in-the-loop is mandatory for match confirmation, but the specific UX pattern (modal, inline action buttons, dedicated review queue page) is unresolved. Decide during Phase 3 planning before building the match review UI.

## Sources

### Primary (HIGH confidence)

- Existing codebase — `backend/app/models/`, `services/scrape_service.py`, `repositories/scrape_result.py`, `scrapers/base.py`, `frontend/src/components/`, `frontend/src/lib/format.ts` — direct analysis confirming data gaps and integration points
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) — MIT license confirmed, C++ core, API documentation
- [RapidFuzz documentation](https://rapidfuzz.github.io/RapidFuzz/) — `token_sort_ratio`, `token_set_ratio`, `cdist` API confirmed current
- [shadcn/ui Table docs](https://ui.shadcn.com/docs/components/radix/table) — confirmed already installed at `frontend/src/components/ui/table.tsx`

### Secondary (MEDIUM confidence)

- [ScrapeOps Monitoring](https://scrapeops.io/monitoring-scheduling/) — scrape health dashboard metrics and patterns
- [CamelCamelCamel vs Keepa](https://goaura.com/blog/camelcamelcamel-vs-keepa) — competitor feature comparison
- [Amazon Price History: 30 vs 90 Days](https://taskmonkey.ai/blog/amazon-price-tracker/amazon-price-history-30-vs-90-days) — time window analysis confirming 30d/90d as industry standard
- [Fuzzy Matching 101 - Data Ladder](https://dataladder.com/fuzzy-matching-101/) — threshold selection guidance, false positive patterns
- [2025 Fuzzy Matching Benchmarks](https://similarity-api.com/blog/speed-benchmarks) — `rapidfuzz` 40% faster than `thefuzz` confirmed
- [SQLite performance tuning - phiresky](https://phiresky.github.io/blog/2020/sqlite-performance-tuning/) — composite index strategy, aggregate query optimization

### Tertiary (LOW confidence)

- [How LLMs Fail on Product Identity](https://blog.affiliate.com/how-llms-fail-on-product-identity-and-how-to-fix-it-with-barcodes-mpns-and-deduplication-rules/) — used to justify avoiding LLM-based matching; directional support for RapidFuzz approach
- [Walmart Product Matching](https://medium.com/walmartglobaltech/product-matching-in-ecommerce-4f19b6aebaca) — e-commerce matching patterns at enterprise scale (directional only — different scale from this tool)

---
*Research completed: 2026-03-22*
*Ready for roadmap: yes*
