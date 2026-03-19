---
phase: 2
slug: scraping-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing from Phase 1) |
| **Config file** | `backend/pyproject.toml` (pytest config section) |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | SCRAPE-01 | unit | `cd backend && python -m pytest tests/scrapers/test_browser_manager.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | SCRAPE-01 | unit | `cd backend && python -m pytest tests/scrapers/test_extractors.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | SCRAPE-01, SCRAPE-04 | unit | `cd backend && python -m pytest tests/scrapers/test_scrape_service.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | SCRAPE-04 | unit | `cd backend && python -m pytest tests/scrapers/test_retry.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 3 | HIST-01, HIST-02 | unit | `cd backend && python -m pytest tests/repositories/test_scrape_result_repository.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 3 | HIST-02 | unit | `cd backend && python -m pytest tests/scrapers/test_delta_calculation.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 3 | SCRAPE-01 | integration | `cd backend && python scripts/scrape.py --help` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/scrapers/__init__.py` — package init
- [ ] `tests/scrapers/test_browser_manager.py` — stubs for BrowserManager lifecycle (SCRAPE-01)
- [ ] `tests/scrapers/test_extractors.py` — stubs for BaseExtractor + 5 retailer extractors (SCRAPE-01)
- [ ] `tests/scrapers/test_scrape_service.py` — stubs for ScrapeService orchestration (SCRAPE-01, SCRAPE-04)
- [ ] `tests/scrapers/test_retry.py` — stubs for exponential backoff, three-tier failure classification (SCRAPE-04)
- [ ] `tests/repositories/test_scrape_result_repository.py` — stubs for ScrapeResult persistence (HIST-01)
- [ ] `tests/scrapers/test_delta_calculation.py` — stubs for price delta math (HIST-02)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Headless patchright fetches live Amazon page | SCRAPE-01 | Requires network + browser binary | Run `python scripts/scrape.py https://www.amazon.com/dp/B08N5WRWNW`, verify structured output printed |
| patchright stealth passes retailer bot detection | SCRAPE-01 | Requires live network; non-deterministic | Run scrape against each of 5 retailers, verify price extracted (not blocked page) |
| CLI script prints structured output without DB writes | SCRAPE-01 | Requires real browser | Run script, check no new rows in `scrape_results` table |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
