---
phase: 6
slug: price-history-visualization-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest 4.1.0 + @testing-library/react 16.3.2 |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Full suite command** | `cd frontend && npx vitest run --reporter=verbose` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx vitest run --reporter=verbose`
- **After every plan wave:** Run `cd frontend && npx vitest run --reporter=verbose`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 0 | HIST-03 | unit | `cd frontend && npx vitest run src/__tests__/PriceChart.test.tsx -x` | ❌ W0 | ⬜ pending |
| 6-02-01 | 02 | 0 | HIST-04 | unit | `cd frontend && npx vitest run src/__tests__/PriceTable.test.tsx -x` | ❌ W0 | ⬜ pending |
| 6-02-02 | 02 | 0 | HIST-05 | unit | `cd frontend && npx vitest run src/__tests__/PriceHistoryView.test.tsx -x` | ❌ W0 | ⬜ pending |
| 6-03-01 | 03 | 0 | UI-02 | unit | `cd frontend && npx vitest run src/__tests__/ThemeToggle.test.tsx -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/__tests__/PriceChart.test.tsx` — stubs for HIST-03 (chart renders, threshold line present)
- [ ] `src/__tests__/PriceTable.test.tsx` — stubs for HIST-04 (table renders, sort toggles work)
- [ ] `src/__tests__/PriceHistoryView.test.tsx` — stubs for HIST-05 (time range filtering)
- [ ] `src/__tests__/ThemeToggle.test.tsx` — stubs for UI-02 (toggle switches theme class)
- [ ] `recharts` install: `cd frontend && npm install recharts`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chart visually renders threshold dashed line | HIST-03 | SVG rendering correctness requires visual inspection | Open a listing with price history; confirm dashed horizontal line at threshold price |
| Dark mode renders correctly across all pages | UI-02 | Full visual fidelity check across components | Toggle dark mode; verify no unthemed elements (white flash, wrong colors) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
