# Deferred Items - Phase 06

## Pre-existing Test Failures (Out of Scope)

1. **QuerySheet.test.tsx line 80**: Test expects `text-emerald-600` but ListingRow uses `text-emerald-400`. Test assertion is stale.
2. **StatusDot.test.tsx line 32**: Test expects `.bg-zinc-400` for paused status but the component uses a different class. Test assertion is stale.

Both failures exist before any Phase 06 changes and are not caused by this plan's work.
