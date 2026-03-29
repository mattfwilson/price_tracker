# Phase 10: Multi-Product Fuzzy Matching - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Detect when retailer URLs across any watch query resolve to the same product using RapidFuzz fuzzy title matching. Run the matching job as a background task after each scrape without blocking the pipeline. Expose a `/matches` page where users review pending suggestions (confirm/reject) and view confirmed match groups side-by-side with current prices, timestamps, and history links.

New nav page, new data tables (match_groups, match_group_members, rejected_pairs), new background service. No changes to existing scraping or watch query flows.

</domain>

<decisions>
## Implementation Decisions

### Match Scope
- **D-01:** Matching is **cross-query** — compare any retailer URL against any other, regardless of which watch query owns them. A URL in "GPU Watch" can match a URL in "Graphics Cards" if their scraped product titles are similar enough.
- **D-02:** Matching unit = **latest scraped product_name per retailer_url** (most recent row from scrape_results for that URL). URLs with zero scrape results are excluded from matching (nothing to compare).
- **D-03:** Re-match on every run — confirmed groups are stable (not broken by re-matching), but new candidates can be proposed alongside them. Rejected pairs are always skipped.

### Matching Job Trigger
- **D-04:** The matching job runs **after each watch query scrape completes** (post-scrape hook in scrape_service.py, async/non-blocking). MATCH-04 — does not block the scrape pipeline.

### Data Model
- **D-05:** Three new tables:
  - `match_groups` — one row per confirmed group (id, created_at)
  - `match_group_members` — junction table (match_group_id, retailer_url_id); multi-member groups supported
  - `rejected_pairs` — pair-level rejection (retailer_url_id_a, retailer_url_id_b, rejected_at); unique constraint on the pair (order-normalized: smaller id always in column a)
- **D-06:** Pending suggestions are **not stored** in the DB — they are computed fresh on each `/matches` page load (or on demand) by running the fuzzy algorithm and filtering out confirmed group members and rejected pairs. No `match_suggestions` table needed.

### Fuzzy Matching Algorithm
- **D-07:** Use RapidFuzz `token_sort_ratio` for title comparison (handles word-order differences across retailers). Apply title normalization before matching: lowercase, strip noise tokens (e.g., "buy", "shop", "new", "free shipping"), collapse whitespace.
- **D-08:** Similarity threshold: **85%** minimum to surface a suggestion. (Research note from STATE.md: threshold needs empirical validation during planning — researcher should verify against real scraped titles in the DB.)

### /matches Page Layout
- **D-09:** Single page at `/matches` with a nav link in the header alongside "Health" and "Alerts". Two sections on the page:
  1. **Pending suggestions (N)** — review cards, shown at top. Empty state if no pending suggestions.
  2. **Confirmed groups** — cards below. Empty state if no confirmed groups.
- **D-10:** Nav link shows a count badge for pending suggestion count, consistent with the Alerts bell pattern.

### Suggestion Review Cards
- **D-11:** Each pending suggestion displays as a card with:
  - Header: `Possible match (XX%)` where XX is the similarity score
  - Two-column body: left = URL A details, right = URL B details
  - Per column: product name, current price (formatted via `formatPrice()`), retailer domain, watch query name
  - Footer: `[Confirm]` and `[Reject]` buttons
- **D-12:** For groups with 3+ members in suggestions (if algorithm detects a cluster): columns wrap or scroll horizontally within the card.

### Confirmed Group Cards
- **D-13:** Same card layout as suggestions, but:
  - Header: `✓ Confirmed match`
  - Per column adds: last scraped timestamp (relative), `[View history]` link to the existing price history view for that listing
  - Lowest-price member is highlighted (badge or color indicator — `[Lowest]` pattern from ListingRow)
  - Footer: `[Unmatch]` button
- **D-14:** Multi-member groups (3+) wrap horizontally inside the card (same as suggestions).

### Reject Persistence
- **D-15:** Rejection is **pair-level** — store a `rejected_pairs` row for (url_id_a, url_id_b). That exact pair never re-surfaces as a suggestion. Either URL can still match a third URL in the future.
- **D-16:** When user clicks `[Unmatch]` on a confirmed group: delete the `match_groups` + `match_group_members` rows, AND insert `rejected_pairs` rows for every pair within the group. Same outcome as if user had rejected each suggestion individually.

### Claude's Discretion
- Exact Tailwind classes, spacing, and card visual design for the /matches page
- Whether pending suggestions are computed in the API endpoint (on-demand) or by a lightweight cached store — pick the approach that avoids stale suggestions without requiring a `match_suggestions` table
- RapidFuzz normalization regex details (which tokens to strip)
- Empty state illustrations/copy for the two sections
- Loading skeleton for the /matches page
- Whether `match_groups` stores the similarity score at group creation time (useful for display)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — MATCH-01 through MATCH-04

### Project constraints
- `.planning/PROJECT.md` — Stack (FastAPI backend, React frontend, SQLite, local-only), single user

### Existing backend (read before adding matching service)
- `backend/app/services/scrape_service.py` — where post-scrape matching hook must be added (async, non-blocking)
- `backend/app/services/scheduler.py` — scheduled_scrape() function; understand the async context for post-scrape hooks
- `backend/app/models/retailer_url.py` — `RetailerUrl` model; matching indexes retailer_url_id
- `backend/app/models/scrape_result.py` — `ScrapeResult`; matching reads `product_name` from latest result per URL
- `backend/app/repositories/scrape_result.py` — existing repo patterns to follow for new match_groups repository

### Existing frontend patterns
- `frontend/src/components/health/HealthTable.tsx` — sortable table pattern; health page is the closest structural analog
- `frontend/src/HealthPage.tsx` — page structure, nav link wiring
- `frontend/src/components/layout/Header.tsx` — where "Matches" nav link + count badge must be added
- `frontend/src/components/query/ListingRow.tsx` — `[Lowest]` badge pattern to reuse in confirmed group cards
- `frontend/src/lib/format.ts` — `formatPrice()` (price display), `formatRelativeTime()` (timestamp display)
- `frontend/src/types/api.ts` — TypeScript type conventions to follow for new match API types

### Prior phase context
- `.planning/phases/08-scrape-health-dashboard/08-CONTEXT.md` — Health page pattern; /matches follows same structure (new route, nav link, dedicated page)
- `.planning/phases/09-wayback-price-comparisons/09-CONTEXT.md` — Badge component usage, `[Lowest]` pattern, formatShortDate

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/ui/badge.tsx` — Badge component for `[Lowest]` highlight on confirmed group cards
- `frontend/src/components/shared/EmptyState.tsx` — empty state for "no pending suggestions" and "no confirmed groups"
- `frontend/src/lib/format.ts` — `formatPrice()`, `formatRelativeTime()`, `formatShortDate()`
- TanStack Query hooks pattern — add `useMatchSuggestions()` and `useMatchGroups()` following existing hook structure
- shadcn/ui `Card` — suggestion/group cards built on the existing Card primitive

### Established Patterns
- New Alembic migration for `match_groups`, `match_group_members`, `rejected_pairs` tables
- New API router `backend/app/api/matches.py` mounted in the FastAPI app
- New frontend page `frontend/src/MatchesPage.tsx` with route `/matches`
- Header nav badge: follows the alerts bell count badge — check alerts nav implementation for pattern
- Dark mode: all new components inherit Tailwind CSS v4 `.dark` theme automatically

### Integration Points
- `backend/app/services/scrape_service.py` — add `await run_fuzzy_matching(session)` (or fire-and-forget) after scrape completes
- `backend/app/core/database.py` — matching service needs async session access
- `frontend/src/components/layout/Header.tsx` — add "Matches" nav link with pending count badge
- `frontend/src/App.tsx` (router) — add `/matches` route pointing to MatchesPage

</code_context>

<specifics>
## Specific Ideas

- Suggestion card mockup confirmed:
  ```
  ┌─────────────────────────────────────────┐
  │ Possible match (89%)                    │
  ├────────────────────┬────────────────────┤
  │ Amazon             │ Best Buy           │
  │ RTX 4080 Gaming    │ RTX 4080 Super OC  │
  │ $589.99            │ $599.99            │
  │ [GPU Watch]        │ [Graphics Cards]   │
  ├────────────────────┴────────────────────┤
  │          [Confirm]    [Reject]          │
  └─────────────────────────────────────────┘
  ```

- Confirmed group card mockup:
  ```
  ┌─────────────────────────────────────────┐
  │ ✓ Confirmed match                       │
  ├────────────────────┬────────────────────┤
  │ Amazon             │ Best Buy           │
  │ RTX 4080 Gaming    │ RTX 4080 Super OC  │
  │ $589.99 [Lowest]   │ $599.99            │
  │ 2h ago             │ 3h ago             │
  │ [View history]     │ [View history]     │
  ├────────────────────┴────────────────────┤
  │                         [Unmatch]       │
  └─────────────────────────────────────────┘
  ```

- Unmatch dissolves group AND inserts rejected_pairs for all member pairs — prevents re-suggestion

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-multi-product-fuzzy-matching*
*Context gathered: 2026-03-28*
