# Phase 1: Data Foundation - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

A working data layer that all subsequent phases can read from and write to, with migration tooling from day one. Delivers: SQLAlchemy models for all 6 tables, Alembic migration setup, repository layer for watch query CRUD, and SQLite configuration (WAL mode, busy_timeout). Does not include API endpoints, scraping logic, or frontend.

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- `backend/` + `frontend/` top-level split — clear boundary, each has its own package manager config
- `backend/app/` organized by layer: `models/`, `repositories/`, `services/`, `api/`, `schemas/`, `core/`
- SQLite database file lives at `backend/data/prices.db` (`.gitignored`)
- Alembic migrations at `backend/alembic/`, config at `backend/alembic.ini`
- `backend/main.py` is the FastAPI entry point

### SQLAlchemy Session Layer
- Async (AsyncSession + aiosqlite) — FastAPI is async-first, keeps event loop unblocked
- Session provided via FastAPI dependency injection: `Depends(get_db)` in `backend/app/core/database.py`
- Route handlers receive `db: AsyncSession` and pass to repository functions
- SQLAlchemy 2.0 `mapped_column()` style with `Mapped[T]` type annotations — full IDE type inference

### app_settings Table
- Single-row typed columns (not key-value pairs) — type-safe, easy to query
- Phase 1 scope: only `default_schedule` column (plus `id` PK and `updated_at`)
- Future phases add columns via Alembic migrations as needed (scrape timeouts, max retries, etc.)

### Alembic Migrations
- Auto-generate from models: `alembic revision --autogenerate -m "description"`, then review + apply
- `env.py` imports `Base.metadata` so Alembic can diff model vs live schema
- Migrations auto-apply on startup: `alembic upgrade head` runs in FastAPI lifespan before the app serves requests — no manual step needed for local dev

### Claude's Discretion
- Exact `core/config.py` structure (Pydantic BaseSettings vs plain dataclass)
- SQLite `busy_timeout` value (something reasonable like 5000ms)
- Whether to seed a default `app_settings` row on first run
- Test setup approach for repository layer

</decisions>

<canonical_refs>
## Canonical References

No external specs — requirements are fully captured in decisions above and in REQUIREMENTS.md.

The following project-level files define constraints downstream agents must respect:
- `.planning/PROJECT.md` — Stack constraints (FastAPI, SQLite, SQLAlchemy, Playwright, APScheduler), key decisions rationale
- `.planning/REQUIREMENTS.md` — HIST-01 (prices as integer cents), success criteria for Phase 1

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — patterns set in Phase 1 become the baseline for all subsequent phases

### Integration Points
- Phase 2 (Scraping Engine) will import `repositories/` to store scrape results and price history
- Phase 3 (API) will import `repositories/` and `schemas/` to expose data via FastAPI routers
- Phase 4+ will use the same session/DI pattern established here

</code_context>

<specifics>
## Specific Ideas

- No specific requirements — open to standard approaches for things under Claude's discretion

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-data-foundation*
*Context gathered: 2026-03-18*
