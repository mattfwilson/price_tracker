# Phase 2: Scraping Engine - Research

**Researched:** 2026-03-18
**Domain:** Web scraping with Playwright-compatible stealth browser, data extraction, retry logic
**Confidence:** MEDIUM

## Summary

Phase 2 builds the scraping engine: a patchright-based browser automation layer that fetches retailer pages, extracts product data via site-specific extractor classes, persists immutable scrape records to SQLite, calculates price deltas, and handles failures with classified retry logic. The entire pipeline is validated via a CLI script before any API exists.

The core stack is patchright (drop-in Playwright replacement with stealth patches) for browser automation, tenacity for retry/backoff logic, and the existing SQLAlchemy async infrastructure for persistence. The main technical risks are (1) retailer CSS selectors being fragile and changing frequently, (2) patchright's recommendation against headless mode conflicting with the user's decision to run headless-only, and (3) the need to manage a persistent browser process lifecycle cleanly.

**Primary recommendation:** Use patchright 1.58.2 with `launch_persistent_context` and `channel="chrome"` for best stealth. Use tenacity for retry decoration. Build extractors as thin classes with a registry pattern keyed on URL domain. Keep the CLI script print-only (no DB writes) as decided.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use **patchright** (drop-in async Playwright replacement with built-in stealth patches) -- not bare Playwright or playwright-stealth plugin
- **Persistent browser context** -- one browser process kept alive, pages opened and closed per scrape. Restarted on error.
- Run **headless** always -- no configurable headed mode needed
- Add **minimal human-simulation**: random delay (0.5-2s) between page navigations only. No mouse movement simulation.
- **Site-specific extractor classes** -- abstract `BaseExtractor` with `extract(url) -> ScrapeData`. Each retailer subclass implements its own CSS selectors and parsing logic.
- Module lives in `backend/app/scrapers/` (separate from `services/`)
- **Phase 2 implements extractors for 5 retailers:** Amazon, Best Buy, Walmart, Newegg, Microcenter
- Extracted data matches exactly what the `ScrapeResult` model needs: `product_name`, `price_cents`, `listing_url`, `retailer_name` -- no extra fields
- **Three-tier failure classification:** NETWORK_ERROR (retryable), EXTRACTION_ERROR (retryable with limit), BLOCKED (hard fail immediately)
- Stored in `ScrapeJob.error_message` with enum prefix (e.g., `NETWORK_ERROR: connection timeout`)
- **Retry policy:** 3 retries with exponential backoff -- wait 2s, 4s, 8s between attempts
- **Partial job success:** If some retailer URLs succeed and others fail, `ScrapeJob.status = 'partial_success'`
- CLI script at `backend/scripts/scrape.py` -- accepts one or more URLs, **print only** (no DB writes), structured output format as specified in CONTEXT.md

### Claude's Discretion
- Exact CSS selectors per retailer (validated against live pages during implementation)
- Browser context configuration details (viewport, user agent string, locale)
- Jitter range for the random delay (within the 0.5-2s guideline)
- How the `BaseExtractor` determines which subclass handles a given URL (domain matching)
- `tenacity` vs manual retry loop for backoff implementation

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCRAPE-01 | System scrapes retailer pages using Playwright headless browser and extracts product name, current price, retailer name, and direct listing URL per page | Patchright as Playwright drop-in; BaseExtractor pattern; per-retailer CSS selectors; ScrapeData dataclass |
| SCRAPE-04 | Scraping failures are retried (2-3x with exponential backoff) and error status with failure reason is surfaced | Tenacity retry decorator with 3 attempts, 2s/4s/8s backoff; three-tier failure classification enum; ScrapeJob.error_message storage |
| HIST-01 | Every scrape result is stored as an immutable historical record: product name, retailer name, price (integer cents), listing URL, and timestamp | Existing ScrapeResult model already has all fields; repository layer for persistence; immutable (no updated_at) |
| HIST-02 | Price delta and percentage change are calculated vs. the previous scrape result for each listing | Query previous ScrapeResult by retailer_url_id ordered by created_at desc; compute delta_cents and pct_change; return alongside current result |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| patchright | 1.58.2 | Stealth browser automation (Playwright drop-in) | Built-in CDP leak patches, drop-in async Playwright API, actively maintained |
| tenacity | 9.1.4 | Retry with exponential backoff | De facto Python retry library, native async support, declarative decorators |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlalchemy | >=2.0.48 (already installed) | Async ORM for scrape result persistence | All DB operations |
| aiosqlite | >=0.22.0 (already installed) | Async SQLite driver | Database access |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tenacity | Manual retry loop | Tenacity is cleaner, handles async natively, but adds a dependency. Manual loop is ~20 lines but less maintainable. Recommend tenacity. |
| patchright | playwright + playwright-stealth | User locked decision: patchright. It bundles stealth patches vs needing a separate plugin. |

**Installation:**
```bash
pip install patchright tenacity
patchright install chromium
```

**Version verification:** patchright 1.58.2 (released 2026-03-07 on PyPI), tenacity 9.1.4 (current on PyPI).

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── scrapers/              # Phase 2 -- NEW module
│   ├── __init__.py
│   ├── base.py            # BaseExtractor ABC, ScrapeData dataclass, FailureType enum
│   ├── registry.py        # Domain-to-extractor mapping, get_extractor(url) function
│   ├── amazon.py           # AmazonExtractor(BaseExtractor)
│   ├── bestbuy.py          # BestBuyExtractor(BaseExtractor)
│   ├── walmart.py          # WalmartExtractor(BaseExtractor)
│   ├── newegg.py           # NeweggExtractor(BaseExtractor)
│   └── microcenter.py      # MicrocenterExtractor(BaseExtractor)
├── services/
│   └── scrape_service.py  # Phase 2 -- NEW: orchestrates browser, extractors, persistence, retry
├── repositories/
│   └── scrape_result.py   # Phase 2 -- NEW: ScrapeResult + ScrapeJob CRUD
└── scripts/               # Phase 2 -- NEW directory (at backend/scripts/)
    └── scrape.py           # CLI validation script
```

### Pattern 1: BaseExtractor Abstract Class
**What:** Abstract base class that each retailer extractor inherits from. Defines the contract for extraction.
**When to use:** Every retailer gets a subclass.
**Example:**
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from patchright.async_api import Page


class FailureType(str, Enum):
    NETWORK_ERROR = "NETWORK_ERROR"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    BLOCKED = "BLOCKED"


@dataclass
class ScrapeData:
    """Matches ScrapeResult model fields exactly."""
    product_name: str
    price_cents: int
    listing_url: str
    retailer_name: str


class ScrapeError(Exception):
    """Raised by extractors with failure classification."""
    def __init__(self, failure_type: FailureType, message: str):
        self.failure_type = failure_type
        self.message = message
        super().__init__(f"{failure_type.value}: {message}")


class BaseExtractor(ABC):
    """Abstract base for site-specific extractors."""

    @property
    @abstractmethod
    def retailer_name(self) -> str:
        """Human-readable retailer name (e.g., 'Amazon')."""
        ...

    @property
    @abstractmethod
    def domain_patterns(self) -> list[str]:
        """URL domain patterns this extractor handles (e.g., ['amazon.com', 'www.amazon.com'])."""
        ...

    @abstractmethod
    async def extract(self, page: Page, url: str) -> ScrapeData:
        """Navigate to URL, extract product data from page. Raise ScrapeError on failure."""
        ...

    def _parse_price_to_cents(self, price_str: str) -> int:
        """Common price parsing: '$1,299.99' -> 129999"""
        cleaned = price_str.replace("$", "").replace(",", "").strip()
        return int(round(float(cleaned) * 100))
```

### Pattern 2: Domain-Based Extractor Registry
**What:** A simple dict mapping URL domains to extractor instances. Resolved at import time.
**When to use:** When `scrape_service` needs to route a URL to the right extractor.
**Example:**
```python
from urllib.parse import urlparse

_REGISTRY: dict[str, BaseExtractor] = {}

def register_extractor(extractor: BaseExtractor) -> None:
    for domain in extractor.domain_patterns:
        _REGISTRY[domain] = extractor

def get_extractor(url: str) -> BaseExtractor:
    hostname = urlparse(url).hostname or ""
    # Try exact match, then strip 'www.'
    extractor = _REGISTRY.get(hostname) or _REGISTRY.get(hostname.removeprefix("www."))
    if not extractor:
        raise ValueError(f"No extractor registered for domain: {hostname}")
    return extractor
```

### Pattern 3: Browser Lifecycle Manager
**What:** A class or context manager that owns the persistent browser context. Pages are created per-scrape and closed after.
**When to use:** The scrape service creates this once, reuses for all scrapes, restarts on browser crash.
**Example:**
```python
import asyncio
import random
from patchright.async_api import async_playwright, BrowserContext

class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._context: BrowserContext | None = None

    async def start(self):
        self._playwright = await async_playwright().start()
        await self._launch_context()

    async def _launch_context(self):
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir="/tmp/patchright_profile",
            channel="chrome",
            headless=True,
            no_viewport=True,
        )

    async def new_page(self):
        if self._context is None:
            await self._launch_context()
        return await self._context.new_page()

    async def restart(self):
        """Restart browser context on error."""
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        self._context = None
        await self._launch_context()

    async def stop(self):
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
```

### Pattern 4: Retry with Tenacity (Async)
**What:** Decorating the per-URL scrape function with tenacity for classified retry.
**When to use:** Each individual URL scrape attempt.
**Example:**
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, ScrapeError):
        return exc.failure_type != FailureType.BLOCKED
    return True  # Network errors from patchright are retryable

@retry(
    stop=stop_after_attempt(4),  # 1 initial + 3 retries
    wait=wait_exponential(multiplier=2, min=2, max=8),  # 2s, 4s, 8s
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def scrape_single_url(browser_manager, url: str) -> ScrapeData:
    extractor = get_extractor(url)
    page = await browser_manager.new_page()
    try:
        # Random delay for human simulation
        await asyncio.sleep(random.uniform(0.5, 2.0))
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return await extractor.extract(page, url)
    except ScrapeError:
        raise
    except TimeoutError:
        raise ScrapeError(FailureType.NETWORK_ERROR, "page load timeout")
    except Exception as e:
        raise ScrapeError(FailureType.NETWORK_ERROR, str(e))
    finally:
        await page.close()
```

### Pattern 5: Price Delta Calculation
**What:** Compare current scrape result to the most recent previous result for the same retailer_url_id.
**When to use:** After persisting a new ScrapeResult.
**Example:**
```python
from sqlalchemy import select, desc

async def calculate_price_delta(
    session: AsyncSession,
    retailer_url_id: int,
    current_price_cents: int,
) -> dict:
    """Returns delta info: direction, delta_cents, pct_change."""
    stmt = (
        select(ScrapeResult.price_cents)
        .where(ScrapeResult.retailer_url_id == retailer_url_id)
        .order_by(desc(ScrapeResult.created_at), desc(ScrapeResult.id))
        .limit(1)
    )
    result = await session.execute(stmt)
    prev_price = result.scalar_one_or_none()

    if prev_price is None:
        return {"direction": "new", "delta_cents": 0, "pct_change": 0.0}

    delta = current_price_cents - prev_price
    pct = (delta / prev_price) * 100 if prev_price != 0 else 0.0

    if delta > 0:
        direction = "higher"
    elif delta < 0:
        direction = "lower"
    else:
        direction = "unchanged"

    return {"direction": direction, "delta_cents": delta, "pct_change": round(pct, 2)}
```

### Anti-Patterns to Avoid
- **Scraping all URLs sequentially in one page:** Open a fresh page per URL, close it after. Do not reuse pages across different URLs -- this avoids state leakage and detection patterns.
- **Storing prices as floats:** The model already uses integer cents. Never convert to float for storage.
- **Committing inside repository methods:** The project pattern is `flush()` in repositories, `commit()` by the caller (service or session context manager).
- **Hardcoding selectors in the service layer:** Keep all CSS selectors inside extractor classes. The service layer should not know about HTML structure.
- **Custom user agents or extra headers with patchright:** Patchright handles fingerprinting automatically. Adding custom headers defeats its stealth patches.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom while-loop with sleep | tenacity `@retry` decorator | Handles async, exception filtering, jitter, attempt counting |
| Browser stealth patches | Manual CDP flag manipulation | patchright (built-in) | CDP leak fixes require deep Chromium internals knowledge |
| Price string parsing | Complex regex per retailer | Shared `_parse_price_to_cents()` on BaseExtractor | Edge cases: commas, currency symbols, ranges, "from $X" |
| URL-to-extractor routing | if/elif chain on URL | Registry dict with domain key lookup | Extensible, testable, no modification to add retailers |

**Key insight:** The extractor classes themselves are the "hand-rolled" part that cannot be avoided -- each retailer has unique HTML structure. But the infrastructure around them (browser management, retry, routing, price parsing) should use proven patterns and libraries.

## Common Pitfalls

### Pitfall 1: Stale CSS Selectors
**What goes wrong:** Retailer sites change their HTML structure frequently. Selectors that worked yesterday break tomorrow.
**Why it happens:** Retailers actively obfuscate class names (especially Amazon with generated class names) and restructure product pages.
**How to avoid:** Use multiple fallback selectors per field. Prefer `[data-*]` attributes and `[itemprop]` semantic attributes over class names. Amazon specifically uses `itemprop="price"` in structured data. Some retailers embed JSON-LD structured data in `<script type="application/ld+json">` tags -- prefer parsing that over CSS selectors when available.
**Warning signs:** EXTRACTION_ERROR rate spikes for a single retailer.

### Pitfall 2: Patchright Headless Detection
**What goes wrong:** Patchright recommends `headless=False` for maximum stealth, but the user decision locks headless-only mode.
**Why it happens:** Modern bot detection can still identify headless Chrome even with patchright patches. Detection scores go from ~67% (headless) to lower with headed mode.
**How to avoid:** Use `channel="chrome"` (not Chromium), `no_viewport=True`, and a persistent context with `user_data_dir`. These reduce the headless fingerprint. For a personal tool making few requests/day, headless mode is likely sufficient -- the out-of-scope section explicitly excludes proxy rotation concerns.
**Warning signs:** Consistent BLOCKED errors across all retailers.

### Pitfall 3: Persistent Context State Pollution
**What goes wrong:** Cookies, localStorage, or cached pages from one retailer leak into scrapes of another retailer.
**Why it happens:** Persistent browser context preserves all state across pages.
**How to avoid:** Clear cookies before each scrape batch, or use `page.context.clear_cookies()` between retailer domains. Alternatively, accept it -- for a personal scraper, cookie accumulation may actually help appear more human-like.
**Warning signs:** Extractors returning wrong retailer data or seeing logged-in/personalized pages.

### Pitfall 4: Page Load Timing
**What goes wrong:** Price elements are rendered by JavaScript after initial DOM load. `page.goto()` with `wait_until="domcontentloaded"` returns before price is visible.
**Why it happens:** Modern retailer sites load prices asynchronously via API calls after initial HTML render.
**How to avoid:** After `goto()`, use `page.wait_for_selector()` on the price element with a reasonable timeout (10-15s). Each extractor should implement its own wait strategy for its known selectors.
**Warning signs:** EXTRACTION_ERROR with "price element not found" despite the page loading successfully.

### Pitfall 5: Price Parsing Edge Cases
**What goes wrong:** Prices appear as "$1,299.99", "From $299.99", "$299.99 - $399.99", or with no decimal.
**Why it happens:** Retailers display prices inconsistently across product types.
**How to avoid:** Strip all non-numeric characters except the decimal point. For range prices, take the first (lowest) price. Validate that the result is a reasonable positive integer (> 0, < 10_000_000 cents / $100K).
**Warning signs:** `price_cents = 0` or unreasonably large values being stored.

### Pitfall 6: patchright install chromium Must Run Post-pip
**What goes wrong:** `pip install patchright` only installs the Python package. The Chromium browser binary must be downloaded separately.
**Why it happens:** Browser binaries are large (~150MB) and platform-specific.
**How to avoid:** Always run `patchright install chromium` after pip install. Document this in setup instructions.
**Warning signs:** `BrowserType.launch: Executable doesn't exist` error at runtime.

## Code Examples

### Retailer Extraction Strategy: JSON-LD Preferred
```python
import json

async def _try_json_ld(self, page: Page) -> ScrapeData | None:
    """Try extracting from JSON-LD structured data (most reliable)."""
    scripts = await page.query_selector_all('script[type="application/ld+json"]')
    for script in scripts:
        text = await script.inner_text()
        try:
            data = json.loads(text)
            # Handle both single object and array
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Product":
                    offers = item.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0]
                    price = offers.get("price")
                    name = item.get("name")
                    if price and name:
                        return ScrapeData(
                            product_name=name,
                            price_cents=int(round(float(price) * 100)),
                            listing_url=str(page.url),
                            retailer_name=self.retailer_name,
                        )
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return None
```

### Scrape Service Orchestration
```python
async def run_scrape_job(
    session: AsyncSession,
    watch_query_id: int,
    browser_manager: BrowserManager,
) -> ScrapeJob:
    """Execute scrape for all retailer URLs in a watch query."""
    job = ScrapeJob(watch_query_id=watch_query_id, status="running", started_at=datetime.utcnow())
    session.add(job)
    await session.flush()

    successes, failures = 0, 0
    # Load retailer URLs
    query = select(RetailerUrl).where(RetailerUrl.watch_query_id == watch_query_id)
    result = await session.execute(query)
    urls = result.scalars().all()

    for retailer_url in urls:
        try:
            data = await scrape_single_url(browser_manager, retailer_url.url)
            scrape_result = ScrapeResult(
                retailer_url_id=retailer_url.id,
                scrape_job_id=job.id,
                product_name=data.product_name,
                price_cents=data.price_cents,
                listing_url=data.listing_url,
                retailer_name=data.retailer_name,
            )
            session.add(scrape_result)
            await session.flush()
            successes += 1
        except ScrapeError as e:
            failures += 1
            # Store error per-result or in job error_message
            job.error_message = (job.error_message or "") + f"\n{retailer_url.url}: {e}"

    job.completed_at = datetime.utcnow()
    if failures == 0:
        job.status = "success"
    elif successes == 0:
        job.status = "failed"
    else:
        job.status = "partial_success"

    await session.flush()
    return job
```

### CLI Script Pattern (Print-Only, No DB)
```python
#!/usr/bin/env python
"""CLI validation script for scraping pipeline. Print-only, no DB writes."""
import asyncio
import sys
from app.scrapers.registry import get_extractor
from app.scrapers.base import ScrapeError

async def main(urls: list[str]):
    browser_manager = BrowserManager()
    await browser_manager.start()
    try:
        for url in urls:
            print(f"\nURL: {url}")
            try:
                extractor = get_extractor(url)
                page = await browser_manager.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    data = await extractor.extract(page, url)
                    print(f"  Retailer:  {data.retailer_name}")
                    print(f"  Product:   {data.product_name}")
                    print(f"  Price:     ${data.price_cents / 100:.2f} ({data.price_cents} cents)")
                    print(f"  Listing:   {data.listing_url}")
                finally:
                    await page.close()
            except ScrapeError as e:
                print(f"  ERROR [{e.failure_type.value}]: {e.message}")
            except ValueError as e:
                print(f"  ERROR [UNKNOWN_RETAILER]: {e}")
    finally:
        await browser_manager.stop()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/scrape.py URL1 [URL2 ...]")
        sys.exit(1)
    asyncio.run(main(sys.argv[1:]))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| playwright-stealth plugin | patchright (built-in patches) | 2024-2025 | No separate plugin needed; patches at CDP level not JS injection |
| Manual retry loops | tenacity decorators | Stable since 2020+ | Cleaner async retry with filtering |
| BeautifulSoup + requests | Playwright/patchright for JS-rendered pages | 2020+ for dynamic sites | Required for Amazon, Walmart, etc. that render prices via JS |
| CSS selectors only | JSON-LD structured data + CSS fallback | Growing adoption 2023+ | More stable extraction when available |

**Deprecated/outdated:**
- `playwright-stealth`: Separate npm plugin approach, less effective than patchright's built-in patches
- `requests` + `beautifulsoup4` for these retailers: Pages render prices via JavaScript, static HTTP won't work

## Open Questions

1. **Patchright headless + `channel="chrome"` on macOS**
   - What we know: patchright recommends headed mode for best stealth; `channel="chrome"` uses system Chrome install
   - What's unclear: Whether `channel="chrome"` works in headless on macOS (requires Chrome to be installed at standard path)
   - Recommendation: Default to `channel="chrome"` with headless, fall back to plain chromium if Chrome not found. Test during implementation.

2. **Retailer CSS selector durability**
   - What we know: Amazon uses generated class names; Walmart embeds data in `__NEXT_DATA__` JSON; Best Buy has relatively stable semantic markup
   - What's unclear: Current exact selectors for all 5 retailers (must validate at implementation time)
   - Recommendation: Implement JSON-LD extraction first (most stable), CSS selectors as fallback. Accept that selectors are inherently fragile and document them clearly.

3. **Persistent context user_data_dir location**
   - What we know: patchright needs a writable directory for browser profile data
   - What's unclear: Best location for a project that runs locally
   - Recommendation: Use a configurable path, default to a temp directory or `~/.price-scraper/browser-profile/`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `backend/pyproject.toml` (asyncio_mode = "auto") |
| Quick run command | `cd backend && python -m pytest tests/ -x -q --timeout=30` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCRAPE-01 | Extractors return ScrapeData with correct fields from mock HTML | unit | `cd backend && python -m pytest tests/scrapers/test_extractors.py -x` | No -- Wave 0 |
| SCRAPE-01 | Registry resolves correct extractor for each retailer URL | unit | `cd backend && python -m pytest tests/scrapers/test_registry.py -x` | No -- Wave 0 |
| SCRAPE-04 | Retry logic retries on NETWORK_ERROR/EXTRACTION_ERROR, not BLOCKED | unit | `cd backend && python -m pytest tests/scrapers/test_retry.py -x` | No -- Wave 0 |
| SCRAPE-04 | Backoff waits are 2s, 4s, 8s (mocked time) | unit | `cd backend && python -m pytest tests/scrapers/test_retry.py::test_backoff_timing -x` | No -- Wave 0 |
| HIST-01 | ScrapeResult persisted with all required fields as immutable record | unit | `cd backend && python -m pytest tests/repositories/test_scrape_result.py -x` | No -- Wave 0 |
| HIST-02 | Price delta calculation: higher/lower/unchanged with correct pct_change | unit | `cd backend && python -m pytest tests/services/test_price_delta.py -x` | No -- Wave 0 |
| HIST-02 | First scrape for a URL returns "new" direction with zero delta | unit | `cd backend && python -m pytest tests/services/test_price_delta.py::test_first_scrape_delta -x` | No -- Wave 0 |
| SCRAPE-01 | CLI script runs end-to-end against live URL (manual smoke test) | manual-only | `cd backend && python scripts/scrape.py <URL>` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q --timeout=30`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/scrapers/__init__.py` -- package init
- [ ] `tests/scrapers/test_extractors.py` -- mock HTML extraction for each retailer
- [ ] `tests/scrapers/test_registry.py` -- domain-to-extractor resolution
- [ ] `tests/scrapers/test_retry.py` -- retry behavior with mocked scrape function
- [ ] `tests/repositories/test_scrape_result.py` -- ScrapeResult and ScrapeJob persistence
- [ ] `tests/services/__init__.py` -- package init
- [ ] `tests/services/test_price_delta.py` -- delta calculation logic
- [ ] `pytest-timeout` dependency -- add to dev dependencies for test timeouts
- [ ] Note: Tests for extractors should use mock HTML fixtures, NOT live network calls. Live validation is manual via CLI script only.

## Sources

### Primary (HIGH confidence)
- [PyPI patchright](https://pypi.org/project/patchright/) - Version 1.58.2, release date 2026-03-07, Python 3.9+ support
- [patchright-python GitHub](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python) - Drop-in Playwright replacement, async API, Chromium-only limitation
- [PyPI tenacity](https://pypi.org/project/tenacity/) - Version 9.1.4, async support via native decorators
- Existing codebase - ScrapeResult, ScrapeJob, RetailerUrl models; async session factory; repository patterns

### Secondary (MEDIUM confidence)
- [roundproxies.com patchright guide](https://roundproxies.com/blog/patchright/) - Configuration recommendations (headless, channel, no_viewport)
- [tenacity docs](https://tenacity.readthedocs.io/) - wait_exponential, retry_if_exception, async support

### Tertiary (LOW confidence)
- CSS selector patterns for retailers - Based on general web scraping knowledge and 2025-2026 guides. Selectors MUST be validated against live pages during implementation as they change frequently.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - patchright and tenacity are verified on PyPI with current versions
- Architecture: HIGH - Patterns follow established project conventions (async, SQLAlchemy 2.0, repository layer)
- Pitfalls: MEDIUM - Retailer-specific risks are well-documented but CSS selector fragility is inherent
- Extraction selectors: LOW - Must validate at implementation time against live pages

**Research date:** 2026-03-18
**Valid until:** 2026-04-01 (patchright updates frequently; retailer HTML changes unpredictably)
