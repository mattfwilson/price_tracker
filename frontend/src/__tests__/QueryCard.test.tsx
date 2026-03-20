import { describe, it, expect } from "vitest";
import { isThresholdBreached } from "@/components/dashboard/QueryCard";

// Testing the pure threshold breach logic extracted from QueryCard.
// Full component testing with TanStack Query provider is deferred
// since the component has complex hook dependencies (useWatchQueryDetail, useScrapeNow).

describe("isThresholdBreached", () => {
  it("returns true when lowest price is below threshold", () => {
    const prices = [45000, 35000, 42000];
    expect(isThresholdBreached(prices, 40000)).toBe(true);
  });

  it("returns true when lowest price equals threshold", () => {
    const prices = [45000, 40000, 42000];
    expect(isThresholdBreached(prices, 40000)).toBe(true);
  });

  it("returns false when all prices are above threshold", () => {
    const prices = [45000, 41000, 42000];
    expect(isThresholdBreached(prices, 40000)).toBe(false);
  });

  it("returns false when no latest_result exists (all null)", () => {
    const prices = [null, null, undefined];
    expect(isThresholdBreached(prices, 40000)).toBe(false);
  });

  it("returns true with mixed null and valid prices where one is below threshold", () => {
    const prices = [null, 35000, undefined, 45000];
    expect(isThresholdBreached(prices, 40000)).toBe(true);
  });

  it("returns false for empty prices array", () => {
    expect(isThresholdBreached([], 40000)).toBe(false);
  });
});
