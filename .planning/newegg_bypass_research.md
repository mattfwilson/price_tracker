# Newegg Bot Detection Bypass Research

**Researched:** 2026-03-20
**Domain:** Browser automation stealth / anti-bot evasion for Newegg.com
**Confidence:** MEDIUM-HIGH (most findings verified across multiple sources; some Newegg-specific details from live page inspection)

---

## Summary

Newegg's "Are you a human?" challenge is served by a **Cloudflare-based protection stack**, not Akamai, PerimeterX, or DataDome. Live inspection of the `/areyouahuman` page confirms `cdn-cgi/challenge-platform/scripts/jsd/main.js` (Cloudflare's JavaScript challenge), plus Google reCAPTCHA v3 and a custom behavioral tracker (mouse velocity/acceleration). Newegg also has a **proprietary image-matching CAPTCHA** (`/human-test/` endpoints) backed by a `BWSTATE` session cookie for verified sessions.

The current setup in `browser.py` uses `headless=True`, which is the **single biggest reason for bot detection**. Patchright's own documentation explicitly states `headless=False` is required for complete stealth — headless mode leaks browser signals that Cloudflare's JS challenge specifically checks. Additionally, `/tmp/patchright_profile` is a red-flag path that never accumulates a real browser history, defeating the purpose of a persistent profile.

**Primary recommendation:** Switch to `headless=False`, use a stable non-temp `user_data_dir`, add random navigation delays, and do not set custom headers or user_agent. For server/CI environments, use `xvfb-run` to provide a virtual display.

---

## 1. What Bot Detection Does Newegg Use?

**Finding: Cloudflare + custom CAPTCHA (not Akamai)**
Confidence: HIGH — verified via direct page inspection of `https://www.newegg.com/areyouahuman`

### Confirmed Detection Layers

| Layer | Technology | Trigger |
|-------|-----------|---------|
| Primary JS challenge | Cloudflare (`cdn-cgi/challenge-platform`) | Any automated browser fingerprint |
| CAPTCHA fallback | Google reCAPTCHA v3 (invisible) | Suspicious behavior score |
| Behavioral analysis | Custom JS (mouse velocity, clicks, timing ~5 sec window) | Robotic navigation patterns |
| Proprietary CAPTCHA | Newegg `/human-test/` image matching | Repeated failures |
| Session token | `BWSTATE` cookie | Issued after passing challenge |
| Redirect | `/areyouahuman?referer=...` | Bot fingerprint on product pages |

### Key Cookie: `BWSTATE`

Newegg issues a `BWSTATE` cookie after a visitor passes its verification. Subsequent page loads check for this cookie. If you can persist this cookie in your Chrome profile across sessions, you skip the challenge entirely until it expires.

The `cf_clearance` cookie (issued by Cloudflare after passing JS challenge) is also present. Cloudflare binds `cf_clearance` to the originating IP + User-Agent combination. If either changes, the cookie becomes invalid.

### What Newegg Does NOT Use (as of March 2026)

Based on research and direct page inspection, Newegg's product pages and bot challenge page show **no evidence** of:
- Akamai Bot Manager (`_abck` / `bm_sz` cookies, `akamai-bm-telemetry` calls)
- PerimeterX / HUMAN Security (`_pxde`, `_pxhd` cookies)
- DataDome (`datadome` cookie)

This is consistent with scraperly.com's independent assessment classifying Newegg as "Light Cloudflare or basic rate limiting" (difficulty 2/5).

---

## 2. The Headless Problem

**Finding: `headless=True` is almost certainly the root cause of current blocking**
Confidence: HIGH — consistent across patchright docs, patchright GitHub, and anti-bot research

### Why `headless=True` Fails

Cloudflare's JavaScript challenge (`cdn-cgi/challenge-platform`) runs active browser checks. In headless mode, Chrome leaks multiple signals regardless of patchright's patches:

- `navigator.userAgent` still contains `HeadlessChrome` in some configurations
- Canvas/WebGL rendering differs from headed Chrome
- `window.chrome.runtime` behaves differently
- Certain GPU/graphics API calls return different results
- Session cookies behave differently (confirmed Chromium upstream bug, not fixed as of Playwright 1.52+)

Patchright's official documentation is unambiguous:

> "To be completely undetected: `headless=False`, `channel="chrome"`, `no_viewport=True`, do NOT add custom browser headers or user_agent."

### Session Cookie Bug (Active as of 2026)

There is a confirmed **Chromium upstream bug** (tracked as Chromium issue #421834902) where session cookies (no `Expires`/`Max-Age`) do not persist across `launch_persistent_context` sessions in headless mode. This means your `user_data_dir` at `/tmp/patchright_profile` is not accumulating the `cf_clearance` or `BWSTATE` cookies between runs when `headless=True`.

**Workaround:** Use `headless=False` (cookies persist correctly) or add `--restore-last-session` to args.

### headless="new" is Not a Playwright Python Option

The `headless="new"` value (a Chromium concept) is **not a valid patchright Python API option**. The Python API accepts only `headless=True` or `headless=False`. The "new headless" mode shipped in Chrome 112+ is what you get when using `channel="chrome"` with `headless=True` — it's the real Chrome binary running headless — but it still exposes headless signals that Cloudflare detects.

---

## 3. Recommended patchright Configuration

### Canonical Best-Practice Launch (from patchright docs)

```python
# Source: https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python (official README)
self._context = await self._playwright.chromium.launch_persistent_context(
    user_data_dir="/home/user/.config/price_scraper_chrome_profile",  # stable, non-tmp path
    channel="chrome",       # real Chrome binary, NOT chromium
    headless=False,         # REQUIRED for stealth — do not use True
    no_viewport=True,       # use native screen resolution
    # DO NOT set: user_agent, extra_http_headers, args with custom fingerprint flags
)
```

### What Patchright Auto-Patches (You Don't Need to Add These)

Patchright automatically handles the following — adding them manually may re-introduce detection vectors or cause conflicts:

| Flag | Patchright Action |
|------|-------------------|
| `--disable-blink-features=AutomationControlled` | Auto-added |
| `--enable-automation` | Auto-removed |
| `--disable-popup-blocking` | Auto-removed |
| `--disable-component-update` | Auto-removed |
| `--disable-default-apps` | Auto-removed |
| `--disable-extensions` | Auto-removed |

**Do not manually pass these in your `args=[]` list.** Patchright manages them at the binary level.

### Args That Are Safe to Add

Only add args that do not affect fingerprint signals:

```python
args=[
    "--restore-last-session",   # helps session cookie persistence if headless=True is ever used
    "--disable-gpu",            # only if running in xvfb/virtual display on a server
    "--no-sandbox",             # only in Docker/CI environments — detection risk otherwise
]
```

**Do not add:**
- `--disable-blink-features=AutomationControlled` (patchright handles it)
- `--window-size` (conflicts with `no_viewport=True`)
- Any `--user-agent` flag (use context options, not args)
- `--headless` (controlled by the `headless=` parameter)

---

## 4. channel="chrome" vs channel="chromium"

**Finding: `channel="chrome"` is correct and important**
Confidence: HIGH — consistent across all patchright documentation

Real users do not browse with Chromium builds. Anti-bot systems (including Cloudflare) have separate fingerprint profiles for:
- `Google Chrome` (from Google's release channel)
- `Chromium` (open-source build — red flag for automation)

`channel="chrome"` requires that a real Chrome binary is installed via `patchright install chrome`. The binary is the same real Chrome browser users download; patchright patches the Playwright communication layer around it, not the binary itself.

```bash
# One-time setup
pip install patchright
patchright install chrome
```

Verify the install worked:
```bash
patchright show-browsers
# Should show: chromium, chrome (if installed)
```

---

## 5. Headers: Set Extra HTTP Headers or Not?

**Finding: Do NOT use `set_extra_http_headers()` or custom `user_agent`**
Confidence: HIGH — explicitly stated in patchright documentation

Custom headers introduce three problems:

1. **Order mismatch**: Chrome sends headers in a specific order. Custom headers added via `set_extra_http_headers()` are appended or injected out of order, which HTTP/2 fingerprinting (used by Cloudflare) detects.
2. **User-Agent inconsistency**: If you override `user_agent`, it must match exactly the TLS fingerprint, canvas fingerprint, WebGL renderer string, and browser version reported by Chrome APIs. Mismatches are an immediate detection signal.
3. **Real Chrome already has correct headers**: `channel="chrome"` means you're running real Chrome with its default headers. Adding custom ones only makes it worse.

**What patchright documentation says verbatim:**
> "do NOT add custom browser headers or user_agent here!"

**If you must set headers** (e.g., language/locale preferences), use browser context options instead:
```python
self._context = await self._playwright.chromium.launch_persistent_context(
    ...
    locale="en-US",
    timezone_id="America/Los_Angeles",
    # These are safe — they're normal browser configuration, not HTTP headers
)
```

---

## 6. User Data Directory Strategy

**Finding: `/tmp/patchright_profile` is counterproductive — use a stable path**
Confidence: HIGH

The purpose of `user_data_dir` for stealth scraping is:

1. Persist `cf_clearance` and `BWSTATE` cookies between runs
2. Accumulate browsing history that makes the profile look like a real user
3. Store Chrome preferences and cached resources

`/tmp/` is cleared on reboot and is a standard path that fingerprinting tools recognize as ephemeral/automated. Use a stable application-specific directory:

```python
import os
from pathlib import Path

CHROME_PROFILE_DIR = Path.home() / ".config" / "price_scraper" / "chrome_profile"
CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
```

### Profile Warming (Optional but Effective)

On first run, the profile is empty — no cookies, no history. Cloudflare and behavioral analysis systems are more suspicious of fresh profiles. Consider:

1. Visit Newegg's homepage first before going to a product page
2. Add a `page.wait_for_timeout(random.randint(2000, 4000))` after navigation
3. On first launch, manually navigate in headed mode so cookies accumulate

### macOS Lock File Bug

On macOS, closing the browser context without also closing the browser object can leave a `SingletonLock` file in `user_data_dir` that prevents the next launch. The fix:

```python
async def stop(self) -> None:
    if self._context:
        browser = self._context.browser()
        await self._context.close()
        if browser:
            await browser.close()   # Required — releases SingletonLock
    if self._playwright:
        await self._playwright.stop()
```

---

## 7. Navigation and Wait Strategy

**Finding: `domcontentloaded` + explicit element wait is better than `networkidle`**
Confidence: HIGH — standard Playwright guidance confirmed across multiple sources

`networkidle` is discouraged for Newegg because:
- Analytics, live chat, and recommendation widgets fire continuously
- Newegg pages may never reach true network idle, causing 30-second timeouts
- Waiting for network idle also gives behavioral systems more time to analyze your automation pattern

**Recommended strategy:**

```python
# In scrape_service.py or the extractor
await page.goto(url, wait_until="domcontentloaded", timeout=30000)

# Then wait specifically for the element you need
await page.wait_for_selector(".price-current", timeout=10000)

# Add human-like pause
await page.wait_for_timeout(random.randint(1500, 3500))
```

For the bot detection check, also handle the redirect:
```python
# Newegg redirects to /areyouahuman when it blocks you
if "areyouahuman" in page.url or "are you a human" in (await page.content()).lower():
    raise ScrapeError(FailureType.BLOCKED, "Cloudflare/Newegg bot challenge triggered")
```

---

## 8. User Agent Rotation

**Finding: Do NOT rotate user agents with patchright + real Chrome**
Confidence: HIGH

User agent rotation is a technique from the pre-fingerprinting era. Modern bot detection correlates:
- The UA string
- Chrome version in the UA
- TLS fingerprint (cipher suites, extensions, ALPN)
- `navigator.userAgent` JS API value
- Canvas/WebGL renderer string (encodes GPU model)
- Chrome version in DevTools protocol

If you change the UA string but not all correlated signals, it is immediately flagged. With `channel="chrome"`, patchright provides a fully consistent real Chrome fingerprint. Rotating the UA breaks that consistency.

**For a personal scraper running infrequently (every few hours), UA rotation provides zero benefit and actively hurts stealth.**

---

## 9. Proxy Usage

**Finding: Not required for a personal low-frequency scraper; helpful for IP bans**
Confidence: MEDIUM

Newegg's Cloudflare configuration is rated "easy" (2/5 difficulty) by scraperly.com. This implies basic Cloudflare without advanced IP reputation scoring. For a scraper running every 6 hours from a home or office connection:

- A residential IP that has browsed Newegg before is low-risk
- Rate limiting typically triggers at ~100 requests/minute per IP
- A personal scraper doing 5-10 product page loads per run is well under this

**However, if you start getting blocked consistently from your home IP**, that IP has likely been flagged. Options:
- Rotate to a residential proxy (Oxylabs, BrightData, SOAX)
- Use a mobile proxy (highest trust score)
- **Do not use datacenter proxies** — Cloudflare identifies datacenter IP ranges and they get blocked readily

For configuring proxy in patchright:
```python
self._context = await self._playwright.chromium.launch_persistent_context(
    user_data_dir=str(CHROME_PROFILE_DIR),
    channel="chrome",
    headless=False,
    no_viewport=True,
    proxy={
        "server": "http://proxy.example.com:8080",
        "username": "user",
        "password": "pass",
    }
)
```

Note: Using a proxy changes the IP that `cf_clearance` is bound to. If you switch proxies mid-session, cached cookies become invalid.

---

## 10. Handling the Bot Challenge Gracefully

### Detection Signals to Check

```python
async def _is_blocked(self, page: Page) -> bool:
    url = page.url
    if "areyouahuman" in url:
        return True
    content = await page.content()
    lower = content.lower()
    # Existing checks
    if "captcha" in lower or "are you a human" in lower:
        return True
    # Cloudflare-specific
    if "cf-browser-verification" in lower or "challenge-platform" in lower:
        return True
    # Newegg proprietary
    if "bwstate" in lower or "/human-test/" in lower:
        return True
    return False
```

### Cookie-Based Session Recovery

If the `BWSTATE` cookie is valid and persisted in `user_data_dir`, subsequent navigations should bypass the challenge entirely. This is why the profile path matters: a fresh `/tmp` profile has no cookies.

To check if the session cookie is present before scraping:
```python
cookies = await self._context.cookies("https://www.newegg.com")
has_bwstate = any(c["name"] == "BWSTATE" for c in cookies)
```

If `BWSTATE` is missing and you hit the challenge, the correct response is to fail gracefully with `FailureType.BLOCKED`, log it, and let the retry scheduler try again later (not immediately — wait at least 10-15 minutes to avoid rate-limit escalation).

---

## 11. Timing and Human-Like Behavior

**Finding: Random delays between 1.5–5 seconds are recommended; mouse simulation is optional for a scraper**
Confidence: MEDIUM

Newegg's behavioral analysis watches mouse velocity and click timing for approximately 5 seconds after page load. For a **read-only price scraper** (not a purchasing bot), the risk profile is lower because:
- You're not clicking "Add to Cart" (which triggers heavier scrutiny)
- You're not navigating search results at inhuman speed
- You're visiting individual product URLs directly

Minimum viable delays:

```python
# After goto()
await page.wait_for_timeout(random.randint(1500, 3500))

# Between scraping multiple pages in one session
await page.wait_for_timeout(random.randint(3000, 6000))
```

For maximum stealth (if needed), add simulated mouse movement before extracting content:
```python
# Move mouse to approximate location of the price element
await page.mouse.move(
    random.randint(400, 800),
    random.randint(300, 600),
    steps=random.randint(5, 15)
)
```

---

## 12. What Wait_Until to Use

**Recommendation: `domcontentloaded` with explicit element waits**
Confidence: HIGH

| Option | Behavior | Verdict for Newegg |
|--------|---------|-------------------|
| `"commit"` | Fires when response headers received | Too early, DOM not built |
| `"domcontentloaded"` | HTML parsed, no stylesheets/images | **Use this** — fast, reliable |
| `"load"` | Full page including static resources | Slower, triggers more analytics |
| `"networkidle"` | No network for 500ms | **Avoid** — Newegg pages may never idle |

```python
await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
await page.wait_for_selector(".price-current, [itemprop='price']", timeout=15_000)
```

The `wait_for_selector` with a comma-separated OR list allows waiting for either the CSS fallback selector or the structured data attribute, whichever renders first.

---

## 13. Server/Headless Environment

If this scraper runs on a Linux server without a display (no GUI), `headless=False` requires a virtual framebuffer.

### Using xvfb (X Virtual Framebuffer)

```bash
# Install
sudo apt install xvfb

# Run scraper with virtual display
xvfb-run --auto-servernum python -m uvicorn main:app
```

Or programmatically via the `xvfbwrapper` Python package:
```python
# In BrowserManager.start()
from xvfbwrapper import Xvfb

self._display = Xvfb(width=1920, height=1080, colordepth=24)
self._display.start()
# ... then launch context
```

Alternatively, consider Docker with:
```dockerfile
RUN apt-get install -y xvfb
ENTRYPOINT ["xvfb-run", "--auto-servernum", "python", "main.py"]
```

**Note:** On macOS (the current dev machine per `.env`), `headless=False` opens a real Chrome window. This is acceptable for a personal local-use app — the window can be minimized.

---

## 14. Patchright Version

**Current stable version:** 1.58.2 (released March 7, 2026)

Patchright tracks Playwright releases closely. Install with:
```bash
pip install patchright
patchright install chrome
```

The package follows Playwright versioning (e.g., patchright 1.58.x = Playwright 1.58.x), so it's kept current.

---

## 15. Alternatives if Patchright Fails

If patchright + headed Chrome stops working against Newegg's Cloudflare (Cloudflare updated detection in February 2025 and broke many tools), these are the next options in order of effort:

| Option | Approach | Complexity | Notes |
|--------|---------|-----------|-------|
| **Nodriver** | CDP-free Chrome automation | Medium | Most actively maintained in 2026, bypasses CDP detection entirely |
| **curl_cffi** | HTTP-only with TLS impersonation | Low | Works for Newegg because it's "basic Cloudflare" — no JS challenge required for most product URLs |
| **SeleniumBase UC Mode** | Undetected Chrome via SeleniumBase | Low-Medium | Well-maintained alternative to patchright |
| **Camoufox** | Modified Firefox instead of Chrome | Medium | Different browser fingerprint, avoids Chrome-specific Cloudflare rules |
| **FlareSolverr** | Sidecar service that gets cf_clearance | Low | Self-hosted proxy that returns solved cookies |

### curl_cffi for Newegg (Worth Trying First)

Given that Newegg's protection is classified as "basic Cloudflare," `curl_cffi` may work without a browser at all for product page loads:

```python
from curl_cffi import requests as cffi_requests

response = cffi_requests.get(
    "https://www.newegg.com/product/...",
    impersonate="chrome124",  # mimics Chrome 124 TLS stack
    headers={"Accept-Language": "en-US,en;q=0.9"},
)
```

If this returns the full product HTML (not a challenge page), you can bypass the browser entirely and use BeautifulSoup for parsing. This would be significantly faster and more reliable than browser automation.

---

## 16. Newegg-Specific CSS and JSON-LD Selectors

The current extractor already uses JSON-LD first, which is correct. JSON-LD is the most stable extraction method because it does not change with UI redesigns.

Confirmed selectors (from scrapers and web scraper marketplace listings):

| Element | Primary Selector | Backup |
|---------|----------------|--------|
| Product title | `script[type="application/ld+json"]` (JSON-LD `name`) | `.product-title` |
| Current price | `script[type="application/ld+json"]` (JSON-LD `offers.price`) | `.price-current strong` + `.price-current sup` |
| Original price | `.price-was-data` | — |
| Availability | JSON-LD `offers.availability` | `.product-inventory` |

Note: `.price-current` renders as `$` + dollars in a `<strong>` + cents in a `<sup>`. The `inner_text()` of the container combines them, but parsing `"$1,23999"` (no decimal separator in text) requires care. JSON-LD `offers.price` is a clean decimal and should always be tried first.

---

## 17. Common Pitfalls

### Pitfall 1: headless=True with patchright (CURRENT BUG IN YOUR CODE)
**What goes wrong:** Cloudflare's JS challenge detects headless Chrome signals and redirects to `/areyouahuman`.
**Why it happens:** Even with patchright's patches, headless mode leaks GPU rendering differences, service worker behavior, and session cookie persistence bugs.
**Fix:** `headless=False`

### Pitfall 2: /tmp profile path
**What goes wrong:** Profile resets on reboot; `BWSTATE` and `cf_clearance` cookies never accumulate.
**Fix:** Use a stable path like `~/.config/price_scraper/chrome_profile`

### Pitfall 3: Immediate retry on BLOCKED
**What goes wrong:** Hammering blocked requests escalates the block, potentially getting your IP flagged more aggressively.
**Fix:** Exponential backoff — wait at least 10-15 minutes before retry. The existing retry logic in `scrape_service.py` should use a longer delay for `BLOCKED` failures specifically.

### Pitfall 4: Setting custom User-Agent
**What goes wrong:** UA string no longer matches TLS fingerprint, canvas, and Chrome version JS APIs. Detected as inconsistent fingerprint.
**Fix:** Never set `user_agent` in context options with `channel="chrome"`.

### Pitfall 5: Calling set_extra_http_headers()
**What goes wrong:** Header injection order is wrong. HTTP/2 fingerprinting detects header order mismatches.
**Fix:** Do not call `set_extra_http_headers()`. Let Chrome send its native headers.

### Pitfall 6: Profile lock file on macOS
**What goes wrong:** `BrowserManager.stop()` closes context but not the browser object. `SingletonLock` left in profile directory. Next launch fails silently or logs errors.
**Fix:** Close `context.browser()` after closing context (see Section 6 above).

### Pitfall 7: networkidle timeout on Newegg
**What goes wrong:** Newegg's analytics/recommendation widgets keep network active. `page.goto(..., wait_until="networkidle")` times out after 30 seconds.
**Fix:** Use `wait_until="domcontentloaded"` followed by explicit `wait_for_selector()`.

---

## 18. Confidence Summary

| Area | Confidence | Source |
|------|-----------|--------|
| Newegg uses Cloudflare (not Akamai) | HIGH | Direct page inspection of `/areyouahuman` |
| `headless=True` is the root cause | HIGH | Patchright docs + multiple anti-bot research sources |
| `headless=False` + `channel="chrome"` is the fix | HIGH | Patchright official README |
| Do not set custom headers/UA | HIGH | Patchright official README |
| `BWSTATE` cookie is the session token | MEDIUM | BuiltWith analysis of Newegg's custom CAPTCHA JS |
| `/tmp` profile counterproductive | HIGH | Chromium cookie persistence bugs confirmed |
| `domcontentloaded` > `networkidle` | HIGH | Playwright docs + scraping community consensus |
| curl_cffi may work without browser | MEDIUM | Newegg classified as "basic Cloudflare" by scraperly.com |
| Residential proxy needed | LOW | Not confirmed needed for low-frequency personal use |

---

## Sources

### Primary (HIGH confidence)
- Patchright Python official README: https://github.com/Kaliiiiiiiiii-Vinyzu/patchright-python
- Patchright PyPI page (version 1.58.2): https://pypi.org/project/patchright/
- Playwright issue #36139 (session cookies bug in headless): https://github.com/microsoft/playwright/issues/36139
- Playwright issue #35466 (macOS persistent context lock bug): https://github.com/microsoft/playwright/issues/35466
- Direct inspection of https://www.newegg.com/areyouahuman (Cloudflare + reCAPTCHA v3 + behavioral JS confirmed)

### Secondary (MEDIUM confidence)
- Scraperly.com Newegg analysis (Cloudflare "easy" 2/5 difficulty): https://scraperly.com/scrape/newegg
- Anti-bot tools comparison (patchright rated highly for Akamai/Cloudflare bypass): https://github.com/pim97/anti-detect-browser-tools-tech-comparison
- ZenRows patchright guide: https://www.zenrows.com/blog/patchright
- RoundProxies patchright guide: https://roundproxies.com/blog/patchright/
- BuiltWith analysis of Newegg's custom CAPTCHA stack (BWSTATE cookie, /human-test/ endpoints)
- browser-use issue #1582 (patchright + Cloudflare regression): https://github.com/browser-use/browser-use/issues/1582

### Tertiary (LOW confidence / community reports)
- Newegg GPU scalper bot discussions (reCAPTCHA + ML detection): https://github.com/jhustles/newegg_webscraper_crawler_dataExtraction_automated
- The Web Scraping Club: Bypassing Akamai for free: https://substack.thewebscraping.club/p/bypassing-akamai-for-free
- DataDome/Akamai bypass proxy guide: https://www.proxies.sx/blog/datadome-akamai-bypass-mobile-proxies

---

## Quick Fix Summary

**To fix the current `browser.py` with minimal changes:**

1. Change `headless=True` to `headless=False`
2. Change `user_data_dir="/tmp/patchright_profile"` to a stable path
3. In `stop()`, close `context.browser()` before `context.close()` (macOS lock bug)
4. In the extractor, change `wait_until` to `"domcontentloaded"` and add `wait_for_selector`
5. Add `random.randint(1500, 3500)` ms delay after navigation

**Do not:**
- Add custom `args=[]` with blink-features flags (patchright handles them)
- Call `set_extra_http_headers()` or set `user_agent`
- Use `wait_until="networkidle"`
- Retry immediately on `BLOCKED` — add a long backoff
