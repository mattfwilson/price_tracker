---
phase: 9
slug: wayback-price-comparisons
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ with pytest-asyncio |
| **Config file** | `backend/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `cd backend && python -m pytest tests/repositories/test_scrape_result.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/repositories/test_scrape_result.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 0 | WAYBACK-01 | unit | `cd backend && python -m pytest tests/repositories/test_scrape_result.py::TestPriceNearDate -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 0 | WAYBACK-04 | unit | `cd backend && python -m pytest tests/repositories/test_scrape_result.py::TestAllTimeExtremes -x` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 0 | WAYBACK-02 | unit | `cd backend && python -m pytest tests/repositories/test_scrape_result.py::TestRollingAvg -x` | ❌ W0 | ⬜ pending |
| 09-01-04 | 01 | 1 | WAYBACK-01, WAYBACK-04 | unit | `cd backend && python -m pytest tests/repositories/test_scrape_result.py -x -q` | ✅ W0 | ⬜ pending |
| 09-02-01 | 02 | 2 | WAYBACK-01, WAYBACK-02, WAYBACK-03, WAYBACK-04 | unit | `cd backend && python -m pytest tests/ -x -q` | ✅ | ⬜ pending |
| 09-02-02 | 02 | 3 | WAYBACK-03 | manual | UI check: deal badge shows green/red/hidden per suppression rules | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/repositories/test_scrape_result.py::TestPriceNearDate` — stubs for WAYBACK-01 (nearest record, None outside window, exact match)
- [ ] `tests/repositories/test_scrape_result.py::TestAllTimeExtremes` — stubs for WAYBACK-04 (per-URL min/max, no results → None)
- [ ] `tests/repositories/test_scrape_result.py::TestRollingAvg` — extend for 90-day window parameter (WAYBACK-02)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Good deal badge shows green when current price < 90d avg | WAYBACK-03 | Frontend display logic — Badge color/visibility is UI-only | Open a watch query detail, confirm green "Good deal" badge when current price is below 90d avg; red "Above avg" when above; hidden when < 3 data points in 90d window |
| Stats row omits missing segments gracefully | WAYBACK-01, WAYBACK-02 | Display layout with variable data — can't automate segment counting | Open detail for URL with partial history; verify absent fields are omitted (no "N/A"), not blank labeled |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
