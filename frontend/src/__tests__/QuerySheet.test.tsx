import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { findLowestPriceUrlId } from "@/components/query/QuerySheet";
import { ListingRow } from "@/components/query/ListingRow";
import type { RetailerUrlWithLatest } from "@/types/api";

function makeUrl(
  id: number,
  priceCents: number | null,
  direction: "new" | "higher" | "lower" | "unchanged" = "new"
): RetailerUrlWithLatest {
  return {
    id,
    url: `https://example.com/product-${id}`,
    created_at: "2026-01-01T00:00:00Z",
    latest_result: priceCents !== null
      ? {
          product_name: `Product ${id}`,
          price_cents: priceCents,
          listing_url: `https://example.com/product-${id}`,
          scraped_at: "2026-01-01T00:00:00Z",
          direction,
          delta_cents: 0,
          pct_change: direction === "lower" ? -5.0 : direction === "higher" ? 5.0 : 0,
        }
      : null,
  };
}

describe("findLowestPriceUrlId", () => {
  it("returns correct id when multiple URLs have different prices", () => {
    const urls = [makeUrl(1, 50000), makeUrl(2, 30000), makeUrl(3, 40000)];
    expect(findLowestPriceUrlId(urls)).toBe(2);
  });

  it("returns null when all latest_result are null", () => {
    const urls = [makeUrl(1, null), makeUrl(2, null)];
    expect(findLowestPriceUrlId(urls)).toBeNull();
  });

  it("handles single URL correctly", () => {
    const urls = [makeUrl(1, 25000)];
    expect(findLowestPriceUrlId(urls)).toBe(1);
  });
});

describe("ListingRow", () => {
  it("renders Lowest badge when isLowest=true", () => {
    const url = makeUrl(1, 30000);
    render(
      <ListingRow url={url} isLowest={true} thresholdCents={50000} />
    );
    expect(screen.getByText("Lowest")).toBeInTheDocument();
  });

  it("does NOT render Lowest badge when isLowest=false", () => {
    const url = makeUrl(1, 30000);
    render(
      <ListingRow url={url} isLowest={false} thresholdCents={50000} />
    );
    expect(screen.queryByText("Lowest")).not.toBeInTheDocument();
  });

  it("renders 'Available in next update' title attribute on history link", () => {
    const url = makeUrl(1, 30000);
    render(
      <ListingRow url={url} isLowest={false} thresholdCents={50000} />
    );
    const historyLink = screen.getByText("View history");
    expect(historyLink).toHaveAttribute("title", "Available in next update");
  });

  it("renders correct delta color for 'lower' direction", () => {
    const url = makeUrl(1, 30000, "lower");
    render(
      <ListingRow url={url} isLowest={false} thresholdCents={50000} />
    );
    // The delta display should contain text-emerald-600 class
    const deltaEl = screen.getByText(/5\.0%/);
    expect(deltaEl.closest("span")).toHaveClass("text-emerald-600");
  });
});
