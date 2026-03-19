---
phase: 4
slug: scheduling-alerts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24.x |
| **Config file** | `backend/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q --timeout=30` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -q --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 0 | SCRAPE-02 | unit | `cd backend && python -m pytest tests/services/test_scheduler.py -x` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 0 | ALERT-01 | unit | `cd backend && python -m pytest tests/services/test_alert_service.py -x` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 0 | ALERT-02, ALERT-03, ALERT-04 | integration | `cd backend && python -m pytest tests/api/test_alerts.py -x` | ❌ W0 | ⬜ pending |
| 4-01-04 | 01 | 1 | SCRAPE-02 | unit | `cd backend && python -m pytest tests/services/test_scheduler.py::test_register_jobs_from_db -x` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | ALERT-01 | unit | `cd backend && python -m pytest tests/services/test_alert_service.py::test_alert_fires_on_breach -x` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 1 | ALERT-01 | unit | `cd backend && python -m pytest tests/services/test_alert_service.py::test_no_alert_continued_breach -x` | ❌ W0 | ⬜ pending |
| 4-02-03 | 02 | 1 | ALERT-01 | unit | `cd backend && python -m pytest tests/services/test_alert_service.py::test_alert_fires_on_rebreach -x` | ❌ W0 | ⬜ pending |
| 4-02-04 | 02 | 1 | ALERT-03 | integration | `cd backend && python -m pytest tests/api/test_alerts.py::test_list_alerts -x` | ❌ W0 | ⬜ pending |
| 4-02-05 | 02 | 1 | ALERT-04 | integration | `cd backend && python -m pytest tests/api/test_alerts.py::test_mark_read -x` | ❌ W0 | ⬜ pending |
| 4-02-06 | 02 | 1 | ALERT-04 | integration | `cd backend && python -m pytest tests/api/test_alerts.py::test_dismiss_all -x` | ❌ W0 | ⬜ pending |
| 4-02-07 | 02 | 1 | ALERT-04 | integration | `cd backend && python -m pytest tests/api/test_alerts.py::test_unread_count -x` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 2 | ALERT-02 | integration | `cd backend && python -m pytest tests/api/test_alerts.py::test_sse_stream -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_scheduler.py` — stubs for SCRAPE-02 (scheduler registration, job add/remove, schedule mapping)
- [ ] `tests/services/test_alert_service.py` — stubs for ALERT-01 (breach detection, re-breach logic, alert creation)
- [ ] `tests/api/test_alerts.py` — stubs for ALERT-02, ALERT-03, ALERT-04 (SSE stream, alert CRUD endpoints)
- [ ] `tests/repositories/test_alert.py` — stubs for alert repository queries (create, list, mark read, count unread)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE disconnect cleanup | ALERT-02 | Browser disconnect behavior requires live browser client | Open app, connect SSE, close browser tab, verify no orphaned connections in logs |
| Scheduler fires at correct interval | SCRAPE-02 | Wall-clock timing verification impractical in unit tests | Set query to 6h schedule, mock time or observe logs for job execution |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
