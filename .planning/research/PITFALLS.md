# Pitfalls Research

**Domain:** Adding scrape health monitoring, wayback price comparisons, and multi-product fuzzy matching to an existing price tracking scraper
**Researched:** 2026-03-22
**Confidence:** HIGH (pitfalls derived from existing codebase analysis + domain research)

## Critical Pitfalls

### Pitfall 1: No Structured Per-URL Failure Data to Build Health Metrics On

**What goes wrong:**
The existing system only creates a `ScrapeResult` row on success. Failures are buried in `ScrapeJob.error_message` as concatenated unstructured text (format: `"{url}: {error}\n"`). To compute per-URL health metrics, you need to know which URLs failed in which jobs. Parsing `error_message` strings with regex is fragile, lossy (no failure type classification), and will break silently when error message formats change. Yet this is the obvious shortcut developers reach for when asked to "add a health dashboard."

**Why it happens:**
The v1.0 design reasonably optimized for the happy path -- store results on success, concatenate errors for debugging. Per-URL failure tracking was not a requirement. When the health dashboard feature arrives, developers try to derive failure data from existing tables rather than adding proper schema support.

**How to avoid:**
1. Add a `scrape_attempt` table that records one row per `(scrape_job_id, retailer_url_id)` with columns: `status` (success/failed), `failure_type` (from existing `FailureType` enum: NETWORK_ERROR, EXTRACTION_ERROR, BLOCKED), `error_message`, `created_at`. Populate for both successes and failures.
2. Update `run_scrape_job` in `scrape_service.py` to write an attempt row in both the `try` and `except` branches of the URL loop (lines 117-133 of current code).
3. Do NOT parse `ScrapeJob.error_message` for per-URL failure data. It is unstructured, does not preserve failure types, and will rot.

**Warning signs:**
- Regex or string splitting on `error_message` appearing in health metric code
- Failure counts that don't add up (partial_success jobs obscure per-URL outcomes)
- Health metrics that miss failures from jobs where some URLs succeeded

**Phase to address:**
Scrape health dashboard phase -- this is a prerequisite schema migration that must happen first, before any health metric computation.

---

### Pitfall 2: Computing Success Rate Over Calendar Windows Instead of Attempt Counts

**What goes wrong:**
Success rate computed as `successful_scrapes / total_scrapes` over "the last 7 days" produces misleading numbers when scrape schedules vary. A URL scraped hourly has 168 data points in 7 days; a URL scraped daily has 7. Two failures out of 168 (98.8% success) and two failures out of 7 (71.4% success) represent the same reliability but look wildly different on the dashboard. Worse, a URL added 2 days ago that has failed twice shows "0% success over 7 days" -- technically true but misleading because the denominator is wrong.

**Why it happens:**
Calendar-window queries are the natural SQL pattern: `WHERE created_at >= now - interval '7 days'`. It feels correct. The schedule-variance problem is non-obvious until you see the dashboard showing wildly different rates for URLs with identical reliability.

**How to avoid:**
1. Compute success rate as `successes / total_attempts` scoped to a fixed number of recent attempts (e.g., "last 20 scrapes for this URL") rather than a calendar window. This normalizes across schedules.
2. Never show a percentage for URLs with fewer than 5 attempts. Show "2/3 successful" for small samples, not "66.7%."
3. For the "last successful scrape" timestamp, query directly -- do not derive from success rate calculations.
4. Show the denominator alongside the rate: "95% (19/20)" so the user can gauge confidence.

**Warning signs:**
- URLs with different schedules showing incomparable metrics on the same dashboard view
- URLs with 1-2 attempts showing alarming failure percentages
- "partial_success" jobs being silently counted as full successes or full failures

**Phase to address:**
Scrape health dashboard phase -- metric computation logic, after the schema migration.

---

### Pitfall 3: Wayback "30 Days Ago" Showing a Price From a Completely Different Date

**What goes wrong:**
The UI shows "30 days ago: $299" but there was no scrape exactly 30 days ago. The query grabs the nearest scrape -- which might be from 45 days ago or 18 days ago -- and labels it "30 days ago." The user makes purchase decisions based on a comparison that does not represent what it claims. This is especially bad for newly added URLs with sparse history.

**Why it happens:**
Scrapes happen on irregular intervals: schedules vary, scrapes fail, URLs get paused and resumed. The `scrape_results.created_at` timestamps never land exactly N days in the past. The naive query `WHERE created_at <= now() - 30 days ORDER BY created_at DESC LIMIT 1` silently returns arbitrarily distant data. The existing history endpoint already deduplicates consecutive same-price records, which further thins the available comparison points.

**How to avoid:**
1. Always display the actual date of the comparison point, not just the label. Show "Feb 20 ($299)" not "30 days ago: $299."
2. Define acceptable proximity windows: "30-day comparison" means the nearest scrape within +/- 3 days of the target date. If no scrape exists in that window, return null and show "No data" in the UI.
3. For averages over periods, show the sample count: "90-day avg: $285 (12 scrapes)." Never compute an average with fewer than 3 data points -- show individual prices instead.
4. Handle the "URL just added" case explicitly: if the URL has less than N days of history, don't show N-day comparisons at all. Show "Added X days ago" instead.

**Warning signs:**
- "30 days ago" label appearing for URLs added last week
- Comparison showing data from 60+ days ago labeled as "30 days ago"
- Averages based on 1-2 data points presented as reliable statistics

**Phase to address:**
Wayback price comparison phase -- data availability validation must be built before any comparison UI renders.

---

### Pitfall 4: Fuzzy Matching False Positives From Retailer Title Noise

**What goes wrong:**
Retailer product titles are packed with noise: "Sponsored", "Renewed", "2-Pack Bundle", "Used - Like New", "with Free Shipping", storage/color variants in the title, promotional badges. A `token_sort_ratio` of 87 between "Samsung Galaxy S24 Ultra 256GB" and "Samsung Galaxy S24 Ultra 256GB 2-Pack Silicone Case Bundle" looks like a match but represents a completely different product. Worse, the same retailer URL may return slightly different `product_name` values across scrapes (Amazon adds/removes "Best Seller" text), causing a URL to fail self-matching over time.

**Why it happens:**
Developers test fuzzy matching with clean, manually typed product names rather than actual scraped titles. The `product_name` field in `ScrapeResult` stores whatever the retailer page returns, which varies wildly in format, length, and noise across retailers -- and even across scrapes of the same URL.

**How to avoid:**
1. Normalize titles before comparison: lowercase, strip known noise tokens (Sponsored, Renewed, Bundle, Pack, Used, Refurbished, Certified, with [accessory]), collapse whitespace, remove non-alphanumeric except hyphens.
2. Extract canonical product identifiers where possible -- model numbers via regex, ASIN from Amazon URLs -- and prefer exact identifier matching over fuzzy title matching.
3. Use `rapidfuzz.fuzz.token_set_ratio` (not `token_sort_ratio` or `ratio`) because it handles extra/missing tokens gracefully.
4. Set a conservative threshold (90+) and require user confirmation for matches in the 80-90 range. Store match confidence alongside groupings.
5. Build a per-retailer noise token list from observing actual scraped titles.

**Warning signs:**
- Products from the same retailer matching each other (different storage tiers, color variants of the same phone)
- Match count growing faster than the number of genuinely overlapping products
- Users seeing obviously wrong groupings they cannot fix

**Phase to address:**
Multi-product fuzzy matching phase. Title normalization must be built and tested with real scraped data before any matching logic runs.

---

### Pitfall 5: Fuzzy Matching Degrades Quadratically and Blocks the Scrape Pipeline

**What goes wrong:**
Naive fuzzy matching compares every product title against every other -- O(n^2). With 50 tracked URLs this is 1,225 comparisons (fast). With 200 URLs it is 19,900 comparisons, and if matching against every historical title variant instead of just current titles, the input space grows with every scrape. Worse, if matching runs synchronously in the scrape completion path, it blocks the response and slows down the entire scrape cycle.

**Why it happens:**
Developers prototype with 10-20 URLs and matching completes in milliseconds. The quadratic growth is invisible at small scale. Additionally, the natural place to trigger matching is "after a scrape completes" -- which leads to synchronous execution in `run_scrape_job`.

**How to avoid:**
1. Match against a canonical title per `retailer_url_id` (the most recent `product_name`), not every historical scrape result. The comparison space is `retailer_urls` count, not `scrape_results` count.
2. Use blocking/bucketing: only compare products whose normalized titles share at least one significant token (brand name, model number). This reduces comparisons dramatically.
3. Run matching asynchronously -- not in the scrape response path. Scrape completes, stores result, matching runs as a separate background task. User sees match results on next dashboard load.
4. Use `rapidfuzz.process.cdist` for batch comparison -- it is implemented in C++ and dramatically faster than Python-level loops.
5. Cache match results and only recompute when a new URL is added or a product name changes significantly.

**Warning signs:**
- Scrape completion time increasing as more URLs are tracked
- Matching triggered on every scrape even when no product names changed
- Matching running in the API request path

**Phase to address:**
Multi-product fuzzy matching phase. The async architecture and bucketing strategy must be decided before writing matching logic.

---

### Pitfall 6: Stale or Slow Health Dashboard From Unbounded Aggregate Queries

**What goes wrong:**
Health metrics require scanning `scrape_results` and `scrape_jobs` with aggregate queries (COUNT, GROUP BY, subqueries per URL). As scrape history grows to thousands of rows, these queries slow down. SQLite is single-writer, so heavy reads during a scrape can cause "database is locked" contention (the app already uses WAL mode, but long-running reads still block writes if they overlap with the WAL checkpoint). Developers add caching to fix this, but then the dashboard shows stale health data -- a URL that just recovered from failures still shows red.

**Why it happens:**
The natural first implementation computes all health metrics on each dashboard page load with fresh queries. It works fine with 100 rows. At 10,000 rows the dashboard takes multiple seconds. At 50,000 rows it is unusable.

**How to avoid:**
1. Denormalize the hottest metrics onto `RetailerUrl`: add `last_success_at`, `last_failure_at`, `consecutive_failures` columns. Update them atomically in `run_scrape_job` when outcomes are determined. Dashboard reads become simple column lookups.
2. For success rate, precompute on scrape completion (increment counters) rather than computing on read.
3. Ensure the composite index `(retailer_url_id, created_at DESC)` exists on `scrape_results` -- it already serves the history endpoint and will serve health queries.
4. If you must run aggregate queries, scope them with LIMIT (last N attempts per URL) and never compute all URL health in a single unbounded query.

**Warning signs:**
- Dashboard load time increasing over weeks/months
- Health status lagging behind actual scrape outcomes by minutes
- SQLite "database is locked" errors coinciding with dashboard loads during active scrapes

**Phase to address:**
Scrape health dashboard phase. Denormalized columns should be added in the same schema migration as the `scrape_attempt` table.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Parse `ScrapeJob.error_message` for per-URL failures | No schema change needed | Fragile regex, breaks on format changes, loses failure type info | Never -- add a `scrape_attempt` table |
| Compute health metrics with aggregate queries on every page load | Simple to implement | Slow dashboard as data grows, SQLite lock contention | Only with <200 total scrape results; migrate to denormalized columns before that |
| Store fuzzy match results only in memory | Fast prototyping | Lost on restart, recomputed wastefully | Only during initial development iteration |
| Use a single global fuzzy threshold for all retailers | Simpler config | Amazon titles need different thresholds than Best Buy titles (different noise levels) | Acceptable for MVP if threshold is conservative (90+) |
| Run matching synchronously in scrape pipeline | See matches immediately after scrape | Blocks scrape completion, scales poorly | Never in production; acceptable in a throwaway prototype |
| Show "30 days ago" without date validation | Simple to build | Misleading comparisons, user trust erosion | Never -- always validate proximity window |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SQLite + health aggregate queries | No composite index on `(retailer_url_id, created_at)` | Add index in migration; denormalize hot metrics to `RetailerUrl` columns |
| RapidFuzz + scraped titles | Comparing raw titles with `fuzz.ratio()` | Normalize titles first (strip noise tokens, lowercase), use `token_set_ratio`, high threshold |
| APScheduler + matching jobs | Running matching synchronously in scrape callback | Fire a separate lightweight background task for matching after scrape completes |
| Wayback queries + timestamps | Using `datetime.now()` (local time) for "N days ago" arithmetic | Use UTC everywhere; `ScrapeResult.created_at` uses SQLite `func.now()` (UTC) -- all comparisons must use UTC |
| Price averages + integer cents | Computing average with Python float division then rounding imprecisely | Compute `SUM(price_cents) / COUNT(*)` in SQL or use Python `statistics.mean` on integers; display conversion to dollars happens only at the API response boundary |
| Alembic migration + denormalized columns | Adding columns without backfilling existing data | Migration must both add columns and run a data migration to populate them from existing `scrape_jobs`/`scrape_results` |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full table scan for "last N scrapes per URL" | Health dashboard takes >1s | Index on `(retailer_url_id, created_at DESC)` + LIMIT | >10K scrape_results rows |
| O(n^2) fuzzy matching on all titles | Matching takes >5s | Bucketing by shared tokens, batch with `cdist` | >200 retailer URLs |
| Recomputing all wayback stats on page load | Detail page takes >2s to render | Cache wayback stats per URL, invalidate only on new scrape for that URL | >1K scrape_results per URL |
| Unindexed GROUP BY on scrape_jobs for health | Health endpoint timeout | Index on `(watch_query_id, status)`, or denormalize to `RetailerUrl` | >5K scrape_jobs |
| Loading all scrape_results into Python for averages | Memory spike, GC pauses | Use SQL aggregates (AVG, COUNT) with WHERE clauses, never SELECT * into Python | >50K rows |
| Matching against all historical titles instead of current canonical | Comparison space grows with every scrape | Use only the latest `product_name` per `retailer_url_id` as canonical | Always wrong -- grows linearly with scrape count |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing "0% success rate" for a URL that hasn't been scraped yet | User thinks URL is broken immediately after adding it | Show "Not yet scraped" for URLs with zero attempts; require minimum 5 attempts before showing percentage |
| Showing "30 days ago: N/A" without explanation | User confused about why there is no comparison data | Show "Added X days ago -- need more history for 30-day comparison" with actual data availability |
| Auto-grouping products without user confirmation | User sees wrong matches, loses trust, can't fix them | Show suggested matches with confidence scores; let user confirm or dismiss; persist overrides |
| Red/green only color coding for health status | Color-blind users can't distinguish; threshold is arbitrary | Always show the number alongside the color indicator; let user configure what counts as "unhealthy" |
| Displaying "average price: $285" without sample count | User makes purchase decisions on an average computed from 2 data points | Always show sample count: "Avg: $285 (12 scrapes)" -- and refuse to show averages under 3 data points |
| Health dashboard showing all URLs equally | Paused URLs clutter the view with stale "last scraped" timestamps | Separate active vs paused URLs; show "Paused" badge; don't flag paused URLs as unhealthy |
| Consecutive failure count without "since when" context | User sees "5 consecutive failures" but does not know if they happened over 5 hours or 5 weeks | Show "5 failures since [date]" or a timeline, not just the count |

## "Looks Done But Isn't" Checklist

- [ ] **Health dashboard:** Shows success rate but does not handle URLs with zero scrape attempts -- verify "no data" state renders distinctly from "0% success"
- [ ] **Health dashboard:** Consecutive failure counter resets on success but does not handle edge case of manually re-enabling a paused query -- verify counter behavior on state transitions
- [ ] **Health dashboard:** "Last successful scrape" timestamp is shown but timezone is not labeled -- verify it displays in user's local time, not raw UTC from SQLite
- [ ] **Health dashboard:** Shows per-URL health but partial_success jobs are handled -- verify a job where 3/4 URLs succeed correctly marks 1 URL as failed and 3 as succeeded
- [ ] **Wayback comparison:** Shows "30-day price" but validates proximity -- verify it returns null (not stale data) when no scrape exists within +/- 3 days of target
- [ ] **Wayback comparison:** Computes averages but handles uniform prices -- verify it displays "$299 (stable)" not "average: $299" when all scrapes in window have the same price
- [ ] **Wayback comparison:** Works for active URLs but handles deleted URLs -- verify historical comparisons still work after a retailer URL is removed from a watch query
- [ ] **Fuzzy matching:** Matches products but persists groupings -- verify match groups survive server restart (stored in DB, not just memory)
- [ ] **Fuzzy matching:** Threshold is set but tested against real titles -- verify with actual scraped titles from Amazon, Best Buy, Walmart, Newegg, and Micro Center (these are the existing extractors)
- [ ] **Fuzzy matching:** User can reject a false match -- verify dismissed matches are persisted and not re-suggested on next matching run
- [ ] **Fuzzy matching:** Handles Unicode in product titles -- verify normalization works with accented characters, em-dashes, and special symbols retailers inject

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Health metrics built on parsed error strings | MEDIUM | Create `scrape_attempt` table; backfill from `scrape_jobs` + `scrape_results` (derive failures from jobs where a URL has no result row); migrate queries |
| Wrong fuzzy matches already shown to user | LOW | Add "unmatch" action to UI; store user overrides in DB; rerun matching excluding overridden pairs |
| Misleading wayback comparisons shipped | LOW | Add actual-date and sample-count to API response; update frontend to display them; no data migration needed |
| Stale cached health metrics causing confusion | LOW | Drop cache; add denormalized columns to `RetailerUrl`; backfill from existing scrape data; dashboard reads new columns |
| O(n^2) matching blocking scrape pipeline | MEDIUM | Extract matching into async background task; refactor `run_scrape_job` to not call matching; existing match data is preserved |
| Success rates computed over calendar windows showing misleading numbers | LOW | Change queries to "last N attempts" pattern; no schema change needed, just query logic update |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| No structured per-URL failure data | Health dashboard (schema migration) | `scrape_attempt` table exists; rows created for both success and failure in `run_scrape_job` |
| Calendar window success rates | Health dashboard (metric computation) | Success rate uses "last N attempts" not calendar window; unit test with URLs on different schedules shows comparable rates |
| Stale/slow aggregate queries | Health dashboard (denormalization) | `RetailerUrl` has `consecutive_failures`, `last_success_at`; dashboard API responds in <200ms with 10K+ scrape results |
| Sparse data wayback comparisons | Wayback comparison (data availability) | API returns actual comparison date + sample count; null returned when proximity window is empty |
| Misleading averages from few points | Wayback comparison (statistics display) | Averages require minimum 3 data points; sample count always in API response |
| False positives from title noise | Fuzzy matching (normalization) | Title normalizer strips noise tokens; test suite uses real scraped titles from each of the 5 supported retailers |
| Quadratic matching performance | Fuzzy matching (architecture) | Matching runs async via background task; uses token bucketing; benchmark shows 500 URLs matched under 1 second |
| No user control over match results | Fuzzy matching (UX) | Matches shown as suggestions with confidence; confirm/dismiss persisted; dismissed pairs excluded from future runs |

## Sources

- Codebase analysis: `backend/app/models/scrape_result.py`, `scrape_job.py`, `retailer_url.py`, `services/scrape_service.py`, `api/scrapes.py`, `scrapers/base.py`
- [RapidFuzz documentation](https://rapidfuzz.github.io/RapidFuzz/) -- token_set_ratio, cdist batch operations
- [Fuzzy Matching 101 -- Data Ladder](https://dataladder.com/fuzzy-matching-101/) -- false positive patterns, threshold selection pitfalls
- [Jaro-Winkler vs Levenshtein -- Flagright](https://www.flagright.com/post/jaro-winkler-vs-levenshtein-choosing-the-right-algorithm-for-aml-screening) -- algorithm tradeoffs for name matching
- [SQLite performance tuning -- phiresky](https://phiresky.github.io/blog/2020/sqlite-performance-tuning/) -- indexing strategies, aggregate query optimization
- [SQLite aggregates -- High Performance SQLite](https://highperformancesqlite.com/watch/aggregates) -- GROUP BY performance, window functions
- [Sparse/intermittent time series -- Nixtla](https://nixtlaverse.nixtla.io/statsforecast/docs/tutorials/intermittentdata.html) -- challenges with sparse observation data
- [Rolling average pitfalls -- FasterCapital](https://fastercapital.com/content/Rolling-Average--Understanding-the-Rolling-Average-for-Time-Series-in-Excel.html) -- window size selection, sparse data biases

---
*Pitfalls research for: Price Tracker v1.1 -- Scrape Health, Wayback Prices, Fuzzy Matching*
*Researched: 2026-03-22*
