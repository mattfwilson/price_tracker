# Phase 9: Wayback Price Comparisons - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 09-wayback-price-comparisons
**Areas discussed:** ListingRow layout, All-time high scope, Good deal indicator, API delivery strategy

---

## ListingRow Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Compact stats row | A second row below price line: `30d: $51.99 (Mar 12) · 90d: ... · avg $50.12 (18 pts)  ✓ Good deal`. Dense but contained. | ✓ |
| Expandable stats section | Stats hidden behind a toggle ('Show context'). Minimal by default, detail on demand. | |
| Always-visible stats block | Full stats block always shown as a distinct section. More vertical space, nothing hidden. | |

**User's choice:** Compact stats row
**Notes:** Mockup confirmed — single compact line below price/delta row, good deal indicator on same row.

---

## All-Time High Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Per-listing (per retailer URL) | Each URL tracks its own high/low. Fits "for each listing" language in WAYBACK-04. Needs new per-URL repo queries. | ✓ |
| Per-query (cross-retailer) | One all-time high/low across all retailer URLs for the watch query. Simpler, uses existing query-level pattern. | |

**User's choice:** Per-listing (per retailer URL)
**Notes:** All-time high and low appear in the stats row per listing, not on the QuerySheet header.

---

## Good Deal Indicator

### Visual treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Icon + text badge | Green `✓ Good deal` / red `↑ Above avg` badge — matches existing Badge component style. | ✓ |
| Icon only | Just a checkmark or arrow icon with tooltip. Minimal, no label. | |
| Price color change | Current price turns green when good deal. No badge needed. | |

**User's choice:** Icon + text badge

### Suppressed state (< 3 data points for 90d avg)

| Option | Description | Selected |
|--------|-------------|----------|
| Hide indicator entirely | No badge shown when insufficient data. Clean — no misleading signals. | ✓ |
| Show 'Insufficient data' | Muted gray label where badge would be. Explicit but adds noise. | |
| You decide | Claude picks the cleanest approach. | |

**User's choice:** Hide indicator entirely

---

## API Delivery Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Embed in detail endpoint | Add wayback fields to `RetailerUrlWithLatest` in existing GET detail response. Single round-trip. | ✓ |
| Separate per-URL endpoint | GET /retailer-urls/{id}/wayback-stats. Lighter initial load, progressive stats reveal. | |

**User's choice:** Embed in detail endpoint
**Notes:** New nullable/optional fields added to `RetailerUrlWithLatest` — no new endpoint needed.

---

## Claude's Discretion

- Exact Tailwind classes and spacing for the compact stats row
- 30d/90d "ago" price lookup strategy (nearest record vs. exact-day)
- Field naming convention for new wayback Pydantic/TypeScript fields
- Loading skeleton for stats row
