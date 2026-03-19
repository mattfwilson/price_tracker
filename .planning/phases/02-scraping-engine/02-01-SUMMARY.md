---
phase: 02-scraping-engine
plan: 01
subsystem: scraping
tags: [patchright, playwright, web-scraping, extractors, registry-pattern, json-ld]

# Dependency graph
requires:
  - phase: 01-data-foundation
    provides: ScrapeResult, ScrapeJob, RetailerUrl models and async session infrastructure
provides:
  - BaseExtractor ABC with ScrapeData/FailureType/ScrapeError contracts
  - Domain-based extractor registry (get_extractor, register_extractor)
  - BrowserManager for persistent patchright browser context
  - Five retailer extractors (Amazon, Best Buy, Walmart, Newegg, Micro Center)
  - Shared JSON-LD extraction and price parsing utilities
affects: [02-scraping-engine, 03-api, 04-scheduling]

# Tech tracking
tech-stack:
  added: [patchright 1.58.2, tenacity 9.1.4, pytest-timeout 2.4.0]
  patterns: [BaseExtractor ABC, domain registry, JSON-LD primary + CSS fallback extraction, mock Page testing]

key-files:
  created:
    - backend/app/scrapers/base.py
    - backend/app/scrapers/registry.py
    - backend/app/scrapers/browser.py
    - backend/app/scrapers/amazon.py
    - backend/app/scrapers/bestbuy.py
    - backend/app/scrapers/walmart.py
    - backend/app/scrapers/newegg.py
    - backend/app/scrapers/microcenter.py
    - backend/app/scrapers/__init__.py
    - backend/tests/scrapers/test_registry.py
    - backend/tests/scrapers/test_extractors.py
    - backend/tests/scrapers/test_browser_manager.py
  modified:
    - backend/pyproject.toml

key-decisions:
  - "Stub extractors created in Task 1 to satisfy registry tests, completed in Task 2"
  - "JSON-LD extraction as shared _try_json_ld method on BaseExtractor for all retailers"
  - "Walmart uses __NEXT_DATA__ as primary strategy before JSON-LD fallback"

patterns-established:
  - "BaseExtractor ABC: retailer_name property, domain_patterns property, extract(page, url) method"
  - "Registry pattern: register_extractor() at module level, get_extractor(url) with www-prefix stripping"
  - "Extraction strategy: JSON-LD primary, CSS selectors fallback, CAPTCHA/block detection"
  - "Mock Page testing: AsyncMock with query_selector_all/query_selector side effects"

requirements-completed: [SCRAPE-01]

# Metrics
duration: 4min
completed: 2026-03-18
---

# Phase 2 Plan 1: Scraping Infrastructure Summary

**BaseExtractor ABC with 5 retailer extractors (Amazon, Best Buy, Walmart, Newegg, Micro Center) using JSON-LD primary + CSS fallback, domain registry, and patchright BrowserManager**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-19T01:57:42Z
- **Completed:** 2026-03-19T02:02:07Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- BaseExtractor ABC with ScrapeData dataclass, FailureType enum, and ScrapeError exception
- Domain-based extractor registry that resolves URLs with/without www prefix
- BrowserManager with persistent patchright context (headless=True, channel="chrome")
- All 5 retailer extractors with JSON-LD primary extraction and CSS selector fallbacks
- 36 unit tests passing using mock Page objects with no network calls
- patchright 1.58.2, tenacity 9.1.4, and pytest-timeout installed

## Task Commits

Each task was committed atomically:

1. **Task 1: Base contracts, registry, browser manager, and dependency install** - `f83fb1e` (feat)
2. **Task 2: Five retailer extractors with mock HTML unit tests** - `726b03c` (feat)

## Files Created/Modified
- `backend/app/scrapers/base.py` - BaseExtractor ABC, ScrapeData, FailureType, ScrapeError, _try_json_ld, _parse_price_to_cents
- `backend/app/scrapers/registry.py` - Domain-to-extractor routing with get_extractor/register_extractor
- `backend/app/scrapers/browser.py` - BrowserManager with persistent patchright context lifecycle
- `backend/app/scrapers/amazon.py` - AmazonExtractor with JSON-LD + #productTitle/.a-price CSS fallback
- `backend/app/scrapers/bestbuy.py` - BestBuyExtractor with JSON-LD + .sku-title/.priceView CSS fallback
- `backend/app/scrapers/walmart.py` - WalmartExtractor with __NEXT_DATA__ + JSON-LD + itemprop CSS fallback
- `backend/app/scrapers/newegg.py` - NeweggExtractor with JSON-LD + .product-title/.price-current CSS fallback
- `backend/app/scrapers/microcenter.py` - MicrocenterExtractor with JSON-LD + h1.product-title/#pricing CSS fallback
- `backend/app/scrapers/__init__.py` - Package init with re-exports and registration imports
- `backend/tests/scrapers/test_registry.py` - 14 tests for base contracts and registry
- `backend/tests/scrapers/test_extractors.py` - 22 tests for all 5 extractors with mock Pages
- `backend/tests/scrapers/test_browser_manager.py` - 1 test for BrowserManager initialization
- `backend/pyproject.toml` - Added patchright, tenacity, pytest-timeout dependencies

## Decisions Made
- Created stub extractors in Task 1 (with NotImplementedError extract methods) to satisfy registry resolution tests, then completed them in Task 2. This maintained TDD discipline while keeping the registry tests honest.
- Placed JSON-LD extraction as a shared method (_try_json_ld) on BaseExtractor rather than duplicating across extractors.
- Walmart uses __NEXT_DATA__ as its primary extraction strategy since Walmart embeds product data in Next.js page props, falling back to JSON-LD and then CSS selectors.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All extraction contracts and implementations ready for Plan 02 (scrape service orchestration)
- BrowserManager ready to be used by scrape_service for page lifecycle
- Registry will resolve URLs to correct extractors when scrape service processes retailer URLs
- CSS selectors are best-effort based on known patterns; live validation will happen during CLI testing (Plan 03)

## Self-Check: PASSED

All 12 created files verified on disk. Both task commits (f83fb1e, 726b03c) verified in git log.

---
*Phase: 02-scraping-engine*
*Completed: 2026-03-18*
