---
phase: 3
slug: api-watch-query-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed) |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `pytest tests/test_api/ -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_api/ -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | QUERY-01 | integration | `pytest tests/test_api/test_app.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | QUERY-01 | integration | `pytest tests/test_api/test_app.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | QUERY-01 | integration | `pytest tests/test_api/test_watch_queries.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | QUERY-02 | integration | `pytest tests/test_api/test_watch_queries.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | QUERY-03 | integration | `pytest tests/test_api/test_watch_queries.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-04 | 02 | 2 | QUERY-04 | integration | `pytest tests/test_api/test_watch_queries.py -x -q` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | SCRAPE-03 | integration | `pytest tests/test_api/test_scrape.py -x -q` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | QUERY-05 | integration | `pytest tests/test_api/test_scrape.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api/__init__.py` — package init
- [ ] `tests/test_api/conftest.py` — `client` fixture using `httpx.AsyncClient` with `ASGITransport` and `get_db` override
- [ ] `tests/test_api/test_app.py` — stubs for QUERY-01 (app startup, health, CORS)
- [ ] `tests/test_api/test_watch_queries.py` — stubs for QUERY-01 through QUERY-04 (CRUD, duplicate URL filtering, pause/resume)
- [ ] `tests/test_api/test_scrape.py` — stubs for SCRAPE-03 and QUERY-05 (on-demand scrape, results/history endpoints)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| BrowserManager cleanup on shutdown | SCRAPE-03 | Requires process inspection to verify Playwright resources released | Start app, trigger scrape, SIGTERM app, check no orphan browser processes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
