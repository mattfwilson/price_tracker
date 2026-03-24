---
phase: 7
slug: advanced-alert-enhancements
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) / vitest (frontend) |
| **Config file** | backend/pytest.ini / frontend/vite.config.ts |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ && cd ../frontend && npx vitest run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run full suite (backend + frontend)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 0 | ALERT-05, ALERT-07 | migration | `cd backend && alembic upgrade head` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 1 | ALERT-05 | unit | `cd backend && python -m pytest tests/test_alert_service.py -k pct_drop -q` | ❌ W0 | ⬜ pending |
| 7-01-03 | 01 | 1 | ALERT-07 | unit | `cd backend && python -m pytest tests/test_alert_service.py -k cooldown -q` | ❌ W0 | ⬜ pending |
| 7-01-04 | 01 | 2 | ALERT-05, ALERT-07 | integration | `cd backend && python -m pytest tests/test_alert_service.py -q` | ❌ W0 | ⬜ pending |
| 7-02-01 | 02 | 1 | ALERT-06 | unit | `cd backend && python -m pytest tests/test_watch_query_service.py -k all_time_low -q` | ❌ W0 | ⬜ pending |
| 7-02-02 | 02 | 1 | ALERT-05, ALERT-06, ALERT-07 | schema | `cd backend && python -m pytest tests/test_schemas.py -q` | ❌ W0 | ⬜ pending |
| 7-02-03 | 02 | 2 | ALERT-05, ALERT-06, ALERT-07 | api | `cd backend && python -m pytest tests/test_api_watch_queries.py -q` | ❌ W0 | ⬜ pending |
| 7-03-01 | 03 | 1 | ALERT-06 | frontend | `cd frontend && npx vitest run src/components/dashboard/QueryCard.test.tsx` | ❌ W0 | ⬜ pending |
| 7-03-02 | 03 | 1 | ALERT-05, ALERT-07 | frontend | `cd frontend && npx vitest run src/components/dashboard/` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_alert_service.py` — stubs for ALERT-05 (pct_drop evaluation), ALERT-07 (cooldown check)
- [ ] `backend/tests/test_watch_query_service.py` — stubs for ALERT-06 (all_time_low detection)
- [ ] `backend/tests/test_schemas.py` — stubs for new fields (pct_drop_threshold, alert_cooldown_hours, is_all_time_low)
- [ ] `backend/tests/test_api_watch_queries.py` — stubs for new API fields in create/update/response
- [ ] `frontend/src/components/dashboard/QueryCard.test.tsx` — stubs for all-time-low badge rendering

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All-time low badge appears on QueryCard in browser | ALERT-06 | UI rendering requires visual confirmation | Load dashboard, create query with multiple scrapes, verify badge shows when price is lowest ever |
| % drop alert fires end-to-end (scrape → alert creation → SSE push) | ALERT-05 | Full pipeline requires live scrape data | Set pct_drop_threshold=5 on a query, trigger on-demand scrape where price drops >5% below 30d avg, verify alert created |
| Alert cooldown prevents second alert in 24h window | ALERT-07 | Requires time-sensitive alert history | Create alert, trigger another scrape within cooldown window, verify no duplicate alert created |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
