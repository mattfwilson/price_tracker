---
phase: 1
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | none — Wave 0 installs |
| **Quick run command** | `pytest tests/data/ -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/data/ -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | foundational | unit | `pytest tests/data/test_models.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | foundational | integration | `pytest tests/data/test_migrations.py -x -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | foundational | unit | `pytest tests/data/test_repository.py -x -q` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | foundational | unit | `pytest tests/data/test_schemas.py -x -q` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | foundational | integration | `pytest tests/data/test_sqlite_config.py -x -q` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | foundational | unit | `pytest tests/data/test_cents.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — test package init
- [ ] `tests/data/__init__.py` — data test package
- [ ] `tests/data/conftest.py` — async engine/session fixtures, file-based SQLite fixture for WAL tests
- [ ] `tests/data/test_models.py` — stubs for model creation/schema validation
- [ ] `tests/data/test_migrations.py` — stubs for Alembic migration up/down
- [ ] `tests/data/test_repository.py` — stubs for CRUD operations
- [ ] `tests/data/test_schemas.py` — stubs for Pydantic schema validation
- [ ] `tests/data/test_sqlite_config.py` — stubs for PRAGMA verification (WAL, busy_timeout)
- [ ] `tests/data/test_cents.py` — stubs for integer cents enforcement
- [ ] `pytest`, `pytest-asyncio`, `aiosqlite` installation

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Alembic migration generates valid SQL | foundational | Requires visual inspection of generated script | Run `alembic revision --autogenerate -m "test"`, inspect generated file |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
