# Feature Research

**Domain:** Price tracker v1.1 -- scrape health monitoring, wayback price comparisons, multi-product fuzzy matching
**Researched:** 2026-03-22
**Confidence:** MEDIUM-HIGH

## Scope

This research covers ONLY the three new v1.1 features. All v1.0 features (watch query CRUD, scraping, price history, alerts, dashboard) are already built and validated. See git history for prior feature research.

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any scrape health dashboard, historical price comparison, or product matching system must have to feel complete.

#### 1. Scrape Health Dashboard

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Per-URL success/fail status | Users need to know which URLs are broken right now | LOW | ScrapeJob already stores status and error_message; aggregate from existing data |
| Last successful scrape timestamp | "When did this last actually work?" is the first health question | LOW | Query MAX(created_at) from scrape_results per retailer_url_id |
| Consecutive failure count | Distinguishes "one-off flake" from "this URL is dead" | LOW | Count recent jobs since last success per URL |
| Error type classification | Users need to know WHY it failed (blocked vs network vs extraction) | LOW | FailureType enum already exists in base.py (NETWORK_ERROR, EXTRACTION_ERROR, BLOCKED); persist it on ScrapeJob |
| Visual health indicators | Red/yellow/green status per URL at a glance | LOW | Frontend only; thresholds on success rate and consecutive failures |
| Filterable/sortable URL list | "Show me all failing URLs" is the core interaction | LOW | Standard table with filter chips for status |

**Existing data that supports this:** The `ScrapeJob` model already tracks `status` (pending/success/failed/partial_success), `error_message`, `started_at`, and `completed_at`. The `FailureType` enum (NETWORK_ERROR, EXTRACTION_ERROR, BLOCKED) exists in `base.py` but is NOT persisted on the job -- it is only used for retry logic in `scrape_service.py`. The main schema change needed is storing failure_type on ScrapeJob or a new per-URL outcome record.

**Key gap:** The current `run_scrape_job` function tracks successes/failures per URL but only stores a concatenated error string. Per-URL outcome (success/fail + type) needs to be individually stored for health aggregation.

#### 2. Wayback Price Comparisons

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Current price vs N-days-ago price | CamelCamelCamel, Keepa, and Amazon native all show this; table stakes | LOW | SQL query: price at closest timestamp to (now - N days) per retailer_url |
| Historical low and high | Every price tracker shows all-time low/high; partially built (all-time low badge exists) | LOW | MIN/MAX aggregation on scrape_results; extend existing all-time low logic |
| 30-day and 90-day average price | Standard time windows per Keepa, Honey, Amazon native | MEDIUM | Rolling average computation on scrape_results within date range |
| "Good deal" / "bad deal" indicator | Users want a quick verdict, not raw numbers to interpret | LOW | Compare current price to 90-day average; below = good deal, above = bad deal |
| Price context displayed inline | Stats shown alongside existing price history, not on a separate page | LOW | API enrichment on existing endpoints; frontend badges/chips in drill-down view |

**Why these specific time windows:** Research shows 30-day and 90-day are industry standard. Amazon native shows 30-90 days. Keepa free tier shows 90 days. Honey defaults to 30 days with options up to 120. The 30-day window captures recent trend; the 90-day window captures seasonal patterns and sale cycles.

**Computation approach:** These stats are read-heavy but change only when new scrape results arrive. Two viable approaches:
1. **Compute on read** -- SQL aggregation queries on each API call. Simpler, fine for SQLite with dozens of products and thousands of results.
2. **Compute on write** -- Recalculate and cache stats after each scrape. More complex but constant-time reads.

Recommendation: Compute on read for v1.1. SQLite handles this scale trivially. Optimize later only if measurably slow.

#### 3. Multi-Product Fuzzy Matching

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Automatic detection of same-product across retailers | Core value prop; without it, the feature does not exist | HIGH | Fuzzy string matching on product_name across different retailer_url_ids within a watch query |
| Confidence score on matches | Users need to know if a match is reliable or a guess | MEDIUM | Expose the similarity score from RapidFuzz |
| Manual confirm/reject of matches | Fuzzy matching always has false positives; user must be able to correct | MEDIUM | UI for match review; persisted accept/reject state |
| Grouped price comparison view | Once matched, show side-by-side prices across retailers | MEDIUM | New UI component; query matched products and their latest prices |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Health trend over time | ScrapeOps compares current health vs historical moving average; shows degradation before total failure | MEDIUM | Store daily health snapshots; show trend sparkline per URL |
| Stale URL auto-detection | Proactively flag URLs not returning data in X days; suggest "pause or remove" | LOW | Cron check on last_success; surface in health dashboard with action buttons |
| Price percentile ranking | "Current price is in the 15th percentile of all prices seen" -- more useful than just average | LOW | Percentile calc on historical prices; single SQL query |
| Price volatility indicator | Flag products with high price variance; "stable" vs "volatile" badge | MEDIUM | Standard deviation over 90 days; helps user decide monitoring cadence |
| Best-price-across-retailers highlight | When fuzzy matches exist, auto-highlight which retailer currently has lowest price | LOW | Simple MIN query across match group; high value, trivial once matching exists |
| Match suggestions queue | Proactively suggest "these might be the same product" on new scrape results | MEDIUM | Run matching after each scrape; surface suggestions in a review UI |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Automatic retry on detected failures | "Just keep trying until it works" | Aggressive retrying gets IPs blocked faster; tenacity retry with 4 attempts and exponential backoff already handles transient failures in scrape_service.py | Show failure clearly in health dashboard; let user manually re-trigger or adjust schedule |
| Real-time scrape status websocket | "I want to see scrapes happening live" | Significant complexity (websocket infra) for a feature used rarely; scrapes take seconds | Poll-based refresh on health dashboard; "last refreshed" timestamp |
| AI/LLM-powered product matching | "Use embeddings to match products" | Massive complexity, requires model hosting or API costs, overkill for dozens of products. Per affiliate.com research, LLMs actually fail at product identity -- they collapse lookalikes (bundles, variants) and over-trust names | RapidFuzz string matching with manual confirmation handles personal-tool scale perfectly |
| Automatic URL discovery for matched products | "Find this product on other retailers automatically" | Requires search engine scraping or API access; fragile, expensive, explicitly out of scope per PROJECT.md | User provides URLs explicitly; matching only groups URLs already tracked |
| Historical price prediction | "Tell me when the price will drop" | Requires ML modeling, large datasets; fundamentally unreliable for most products | Show volatility and trend direction instead; let user make the judgment call |
| Normalized $/unit comparison | "Compare price per unit across pack sizes" | Requires parsing quantities and units from unstructured titles; error-prone | Show raw prices with product names; user sees "Pack of 2" in the title |
| Cross-query product matching | "Match products across different watch queries" | Significantly increases matching complexity and false positive rate; user intent is already encoded in watch query grouping | Match only within a watch query's retailer URLs; cross-query is v2+ if ever |

## Feature Dependencies

```
[Scrape Health Dashboard]
    +--requires--> [Persisted per-URL scrape outcome] (schema change: add failure_type to ScrapeJob or new outcome table)
    +--requires--> [Health stats aggregation endpoint] (new API)
    +--enhances--> [Existing dashboard query cards] (add health indicator dot)

[Wayback Price Comparisons]
    +--requires--> [Sufficient historical scrape data] (existing; just needs time to accumulate)
    +--requires--> [Price stats computation] (new service/queries)
    +--enhances--> [Existing price history view] (adds stat overlays and badges)
    +--enhances--> [Existing all-time low badge] (extends with more context)

[Multi-Product Fuzzy Matching]
    +--requires--> [RapidFuzz pip dependency] (new)
    +--requires--> [Product match group model] (new DB table)
    +--requires--> [Match computation service] (new backend service)
    +--enhances--> [Scrape Health Dashboard] (view health per match group)
    +--enhances--> [Wayback Price Comparisons] (cross-retailer price context)

[Manual Match Confirmation]
    +--requires--> [Multi-Product Fuzzy Matching]

[Best-Price-Across-Retailers]
    +--requires--> [Multi-Product Fuzzy Matching]
    +--requires--> [Grouped price comparison view]
```

### Dependency Notes

- **Scrape Health Dashboard is fully independent.** Can be built first with zero dependencies on the other two features. Uses existing ScrapeJob/ScrapeResult data with minor schema additions.
- **Wayback Price Comparisons is fully independent.** Only needs existing scrape_results table. Pure computation on historical data already stored.
- **Fuzzy Matching depends on neither but enhances both.** Once match groups exist, health can be viewed per product (across retailers) and price comparisons become cross-retailer.
- **Build order implication:** Health and Wayback can be built in parallel. Fuzzy Matching should come last because it enhances the other two and has the longest tail (matching + review UI + grouped view).

## MVP Definition

### Launch With (v1.1 Core)

- [ ] Per-URL health status with success rate, last success, consecutive failures, and error type -- minimum useful health dashboard
- [ ] Visual health indicators (red/yellow/green) on existing dashboard cards -- immediate visibility without navigating to health page
- [ ] Filterable health URL list -- "show me all failing URLs" flow
- [ ] 30-day and 90-day price-ago comparisons -- "price 30 days ago was $X"
- [ ] 30-day and 90-day average price -- standard context stats
- [ ] Historical low/high display extending existing all-time low badge
- [ ] Good deal / bad deal indicator based on 90-day average
- [ ] Automatic fuzzy matching with confidence scores using RapidFuzz
- [ ] Manual confirm/reject for match suggestions -- mandatory because fuzzy matching always has false positives
- [ ] Grouped comparison view for confirmed matches -- the payoff; without this, matching is pointless

### Add After Validation (v1.1+)

- [ ] Health trend sparklines -- add once users check health dashboard regularly and want to see degradation over time
- [ ] Price volatility indicator -- add once enough historical data exists (needs 30+ data points per URL)
- [ ] Price percentile ranking -- easy to add once price stats service exists
- [ ] Stale URL auto-detection with suggested actions -- add once health dashboard proves useful
- [ ] Best-price-across-retailers highlight -- low effort once matching is built

### Future Consideration (v2+)

- [ ] Health alerting (notify when a URL degrades) -- deferred because notifications are out of scope
- [ ] Match group price alerts (alert when any retailer in a group drops) -- requires notification infrastructure
- [ ] Cross-query product matching -- significantly increases complexity

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Per-URL health status (success rate, last success, failures) | HIGH | LOW | P1 |
| Error type persistence and display | HIGH | LOW | P1 |
| Visual health indicators (red/yellow/green) | HIGH | LOW | P1 |
| Filterable URL health list | MEDIUM | LOW | P1 |
| 30d/90d price-ago comparison | HIGH | LOW | P1 |
| Historical low/high display | HIGH | LOW | P1 |
| 30d/90d average price | HIGH | MEDIUM | P1 |
| Good deal / bad deal indicator | MEDIUM | LOW | P1 |
| Automatic fuzzy matching (RapidFuzz) | HIGH | MEDIUM | P1 |
| Match confidence scores | HIGH | LOW | P1 |
| Manual confirm/reject matches | HIGH | MEDIUM | P1 |
| Grouped price comparison view | HIGH | MEDIUM | P1 |
| Best-price-across-retailers highlight | MEDIUM | LOW | P2 |
| Health trend sparklines | MEDIUM | MEDIUM | P2 |
| Stale URL auto-detection | MEDIUM | LOW | P2 |
| Price percentile ranking | LOW | LOW | P3 |
| Price volatility indicator | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for v1.1 milestone
- P2: Should have, add if time permits within v1.1
- P3: Nice to have, defer to v1.2+

## Competitor Feature Analysis

| Feature | CamelCamelCamel | Keepa | ScrapeOps (scrape monitoring) | Our Approach |
|---------|-----------------|-------|-------------------------------|--------------|
| Price history chart | Full history since 2008; simple clean graphs | 90d free / full paid; detailed multi-line charts with Buy Box, used, 3P | N/A | Already built; enhance with stat overlay lines |
| Historical price stats | Low/high/average per timeframe categories | Hourly granularity, percentiles, sales rank | N/A | 30d/90d avg, all-time low/high, price-ago comparison, good/bad deal badge |
| Scrape health monitoring | N/A (API-based, internal only) | N/A | Success rates, error rates, latency, health vs moving avg, CAPTCHA detection | Per-URL success rate, consecutive failure count, error type, filterable list |
| Cross-retailer matching | Amazon-only, no cross-retailer | Amazon-only | N/A | RapidFuzz on product titles within watch query, manual confirmation |
| Deal assessment | Price drop alerts | Price drop alerts + sales rank correlation | N/A | Good/bad deal badge based on 90d average comparison |

## Fuzzy Matching: Reliability Deep-Dive

This is the highest-risk feature in the milestone. Research findings on what makes matching reliable vs noisy.

### What Makes Matching Reliable

1. **Normalize before comparing.** Strip retailer-specific prefixes/suffixes, normalize case, punctuation, and whitespace. "Samsung Galaxy S24 Ultra 256GB" vs "SAMSUNG Galaxy S24 Ultra, 256 GB" should score high after normalization.

2. **Use token-based similarity, not character-based.** RapidFuzz `token_sort_ratio` and `token_set_ratio` handle word reordering and subset matching. Character-based Levenshtein alone fails on product titles because retailers freely reorder words ("Samsung 65-inch QLED TV" vs "65\" Samsung QLED Smart TV").

3. **Set a conservative threshold (85-90%).** Research consistently recommends starting high and lowering only if too few matches. Per Data Ladder: "Setting the similarity threshold too low leads to merging incorrect data." Start at 85%.

4. **Scope matches within watch query.** The app architecture already groups retailer URLs by watch query, which represents one product intent. Only match within a query's URLs. This dramatically reduces false positives compared to matching across all products.

5. **Human-in-the-loop is mandatory.** Per affiliate.com research, even barcode-based matching needs human verification. Fuzzy title matching absolutely needs confirm/reject. Unreviewed automatic grouping will produce false positives (e.g., matching a phone case with the phone).

### What Makes Matching Noisy

1. **Retailer-specific title padding.** Amazon adds "Visit the X Store" and brand lines. Walmart appends item counts and seller info. Best Buy adds internal SKUs. Pre-normalization must strip these.

2. **Variant confusion.** "iPhone 16 128GB Black" vs "iPhone 16 256GB White" score very high but are different products. Title-only matching cannot reliably distinguish storage/color/size variants.

3. **Bundle vs single items.** "AirPods Pro (2-pack)" vs "AirPods Pro" match with high confidence but are different purchases.

4. **Model year/generation drift.** "Sony WH-1000XM5" vs "Sony WH-1000XM4" differ by one character but are different products.

### Recommended Matching Strategy

Given the app's scope (personal tool, dozens of products, not thousands):

- **Library:** RapidFuzz (MIT license, C++ backend, 40% faster than TheFuzz, same API). Use `token_set_ratio` for primary scoring.
- **Pre-normalization pipeline:** Lowercase, strip common retailer prefixes ("Visit the X Store"), remove punctuation except hyphens in model numbers, normalize whitespace, strip trailing parenthetical info like "(Renewed)" or "(2-pack)".
- **Threshold:** 85% initial, surface matches above that as suggestions.
- **Scope:** Within a single watch query's retailer URLs only.
- **Workflow:** Auto-detect on each new scrape result, queue suggestions, user confirms or rejects, confirmed matches persist, rejected pairs are not re-suggested.
- **Storage:** New `product_match_group` table with status (suggested/confirmed/rejected), similarity score, and retailer_url pair references.

### Why Not More Sophisticated Approaches

- **Barcodes/UPC/MPN:** The app scrapes retailer pages, not product databases. Barcodes are rarely on the rendered page. Would require additional scraping logic per retailer. Overkill for personal tool scale.
- **Image matching:** Would require downloading and comparing product images. Massive complexity increase. Product titles are sufficient for the use case.
- **Embeddings/semantic matching:** Requires a model (local or API). Adds dependency, latency, and complexity. RapidFuzz handles the personal-tool scale. Reserve this for if title matching proves insufficient.

## Sources

- [ScrapeOps Monitoring](https://scrapeops.io/monitoring-scheduling/) -- scrape health dashboard metrics and patterns
- [CamelCamelCamel](https://camelcamelcamel.com/) -- price tracker UI patterns, historical stats
- [Amazon Price History: 30 vs 90 Days](https://taskmonkey.ai/blog/amazon-price-tracker/amazon-price-history-30-vs-90-days) -- time window analysis for price trackers
- [CamelCamelCamel vs Keepa](https://goaura.com/blog/camelcamelcamel-vs-keepa) -- competitor feature comparison
- [How LLMs Fail on Product Identity](https://blog.affiliate.com/how-llms-fail-on-product-identity-and-how-to-fix-it-with-barcodes-mpns-and-deduplication-rules/) -- product matching pitfalls, why barcodes beat names
- [Fuzzy Matching 101 - Data Ladder](https://dataladder.com/fuzzy-matching-101/) -- matching algorithm categories and threshold guidance
- [Walmart Product Matching](https://medium.com/walmartglobaltech/product-matching-in-ecommerce-4f19b6aebaca) -- e-commerce matching at scale
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) -- recommended fuzzy matching library, MIT license, C++ performance
- [2025 Fuzzy Matching Benchmarks](https://similarity-api.com/blog/speed-benchmarks) -- RapidFuzz 40% faster than TheFuzz
- [ScraperAPI Analytics](https://docs.scraperapi.com/account-management/analytics) -- domain-level scrape analytics patterns

---
*Feature research for: Price tracker v1.1 -- scrape health, wayback prices, fuzzy matching*
*Researched: 2026-03-22*
