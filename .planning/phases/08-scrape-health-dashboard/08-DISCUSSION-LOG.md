# Phase 8: Scrape Health Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Session date:** 2026-03-23

---

## Area 1: Per-URL Failure Storage

**Q: How should per-URL scrape attempt outcomes be stored?**
Options presented:
- New table: `scrape_url_attempts` (Recommended) — one row per URL per attempt with retailer_url_id, scraped_at, is_success, error_type, error_message
- Cached columns on RetailerUrl — add consecutive_failures, last_success_at, etc. directly to retailer_urls table
- Compute from existing data — infer from gaps in ScrapeResult + ScrapeJob.error_message

→ **Selected:** New table: `scrape_url_attempts`

**Q: What error types should be tracked?**
Options presented:
- Simple string / freeform (Recommended)
- Enum: blocked / network / parse / timeout / unknown
- You decide

→ **Selected:** You decide (Claude picks based on existing BaseExtractor failure patterns)

---

## Area 2: Health Thresholds + N Window

**Q: What window size N should 'last N attempts' use?**
Options presented:
- 10 attempts (Recommended)
- 5 attempts
- 20 attempts
- Configurable

→ **Selected:** 10 attempts

**Q: What success rate thresholds define healthy / degraded / failing?**
Options presented:
- ≥80% healthy · 50-79% degraded · <50% failing (Recommended)
- ≥90% healthy · 70-89% degraded · <70% failing
- 100% healthy · any failure = degraded · ≥3 consecutive = failing

→ **Selected:** ≥80% healthy · 50-79% degraded · <50% failing

---

## Area 3: Card Health Indicators

**Q: How should per-URL health appear on QueryCard?**
Options presented:
- Per-URL mini-dots below status line (Recommended) — small colored dots, one per URL, tooltip with domain + success rate + last success
- Worst-URL rollup badge — single badge showing worst health state (e.g., "1 failing")
- Replace existing StatusDot — swap current scrape-job status for health-based status

→ **Selected:** Per-URL mini-dots below status line

**Q: What appears on hover/tooltip?**
Options presented:
- Domain + success rate + last success (Recommended) — e.g., "amazon.com · 8/10 · last success 2h ago"
- Domain + health label only — e.g., "amazon.com · Degraded"
- You decide

→ **Selected:** Domain + success rate + last success

---

## Area 4: Health Page Navigation

**Q: How should the health page be reached?**
Options presented:
- Nav item in header (Recommended) — add "Health" link alongside Alerts
- Link from dashboard only — a "View health" link, not in the nav
- You decide

→ **Selected:** Nav item in header

**Q: What does each row on the health page show, and what actions are available?**
Options presented:
- Read-only: URL, query name, status, success rate, last success, consecutive failures, last error (Recommended)
- Same + inline Scrape Now button
- Same + Remove URL button

→ **Selected:** Read-only (no inline actions)
