---
phase: 5
slug: dashboard-frontend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest + React Testing Library |
| **Config file** | `frontend/vitest.config.ts` (Wave 0 creates) |
| **Quick run command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd frontend && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | DASH-01 | unit | `cd frontend && npx vitest run --reporter=verbose` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | DASH-01 | unit | `cd frontend && npx vitest run --reporter=verbose` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | DASH-01 | unit | `cd frontend && npx vitest run src/__tests__/DashboardPage.test.tsx -t "renders query cards"` | ❌ W0 | ⬜ pending |
| 5-02-02 | 02 | 1 | DASH-02 | unit | `cd frontend && npx vitest run src/__tests__/QueryCard.test.tsx -t "threshold breach"` | ❌ W0 | ⬜ pending |
| 5-02-03 | 02 | 1 | DASH-04 | unit | `cd frontend && npx vitest run src/__tests__/StatusDot.test.tsx` | ❌ W0 | ⬜ pending |
| 5-03-01 | 03 | 2 | DASH-03 | unit | `cd frontend && npx vitest run src/__tests__/QuerySheet.test.tsx -t "listings"` | ❌ W0 | ⬜ pending |
| 5-03-02 | 03 | 2 | UI-01 | unit | `cd frontend && npx vitest run src/__tests__/QuerySheet.test.tsx -t "lowest badge"` | ❌ W0 | ⬜ pending |
| 5-03-03 | 03 | 2 | DASH-03 | unit | `cd frontend && npx vitest run src/__tests__/QueryFormDialog.test.tsx` | ❌ W0 | ⬜ pending |
| 5-04-01 | 04 | 2 | DASH-01 | unit | `cd frontend && npx vitest run src/__tests__/BellDropdown.test.tsx` | ❌ W0 | ⬜ pending |
| 5-04-02 | 04 | 2 | DASH-01 | unit | `cd frontend && npx vitest run src/__tests__/AlertLogTable.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/vitest.config.ts` — Vitest configuration with jsdom environment
- [ ] `frontend/src/test/setup.ts` — Testing library setup (jsdom, cleanup, jest-dom matchers)
- [ ] `frontend/src/__tests__/DashboardPage.test.tsx` — stubs for DASH-01, DASH-02
- [ ] `frontend/src/__tests__/QueryCard.test.tsx` — stubs for DASH-01, DASH-02, DASH-04
- [ ] `frontend/src/__tests__/StatusDot.test.tsx` — stubs for DASH-04
- [ ] `frontend/src/__tests__/QuerySheet.test.tsx` — stubs for DASH-03, UI-01
- [ ] `frontend/src/__tests__/QueryFormDialog.test.tsx` — stubs for DASH-03
- [ ] `frontend/src/__tests__/BellDropdown.test.tsx` — stubs for DASH-01 (alerts)
- [ ] `frontend/src/__tests__/AlertLogTable.test.tsx` — stubs for DASH-01 (alerts)
- [ ] Dev deps install: `npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE toast appears when alert fires | DASH-01 | Requires live backend SSE stream | Run backend, trigger scrape below threshold, verify toast appears bottom-right within 5s |
| SSE reconnects after backend restart | DASH-01 | Requires process restart | Stop backend, verify reconnect attempt in 3s, restart backend, verify events resume |
| Google Fonts load correctly | UI-01 | Visual/network | Open devtools Network tab, verify DM Sans + Outfit loaded from fonts.googleapis.com |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
