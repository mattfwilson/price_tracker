---
phase: 8
slug: scrape-health-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) / vitest (frontend) |
| **Config file** | backend/pytest.ini / frontend/vite.config.ts |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ && cd ../frontend && npm test -- --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ && cd ../frontend && npm test -- --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | HEALTH-01 | unit | `cd backend && python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | HEALTH-01 | unit | `cd backend && python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 08-02-01 | 02 | 2 | HEALTH-02 | unit | `cd backend && python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 08-02-02 | 02 | 2 | HEALTH-03 | integration | `cd backend && python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 08-03-01 | 03 | 3 | HEALTH-04 | e2e/manual | manual | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_scrape_health.py` — stubs for HEALTH-01, HEALTH-02, HEALTH-03
- [ ] `backend/tests/conftest.py` — shared fixtures (scrape_url_attempts, health status)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard query cards display health indicator | HEALTH-04 | Visual UI validation | Open dashboard, verify each QueryCard shows colored health dot; check green/yellow/red states |
| Health page sort and filter UI | HEALTH-03 | Interactive UI behavior | Navigate to /scrape-health, verify sort by status/watch query/last success, filter to degraded/failing |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
