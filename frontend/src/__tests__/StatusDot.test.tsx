import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusDot, deriveStatus } from "@/components/dashboard/StatusDot";
import type { WatchQueryDetailResponse } from "@/types/api";

describe("StatusDot", () => {
  it("renders emerald dot for ok status", () => {
    const { container } = render(<StatusDot status="ok" />);
    expect(screen.getByText("OK")).toBeInTheDocument();
    const dot = container.querySelector(".bg-emerald-500");
    expect(dot).toBeInTheDocument();
  });

  it("renders red dot for error status", () => {
    const { container } = render(<StatusDot status="error" />);
    expect(screen.getByText("Error")).toBeInTheDocument();
    const dot = container.querySelector(".bg-red-500");
    expect(dot).toBeInTheDocument();
  });

  it("renders amber dot for running status", () => {
    const { container } = render(<StatusDot status="running" />);
    expect(screen.getByText("Running")).toBeInTheDocument();
    const dot = container.querySelector(".bg-amber-500");
    expect(dot).toBeInTheDocument();
  });

  it("renders zinc dot for paused status", () => {
    const { container } = render(<StatusDot status="paused" />);
    expect(screen.getByText("Paused")).toBeInTheDocument();
    const dot = container.querySelector(".bg-zinc-400");
    expect(dot).toBeInTheDocument();
  });
});

describe("deriveStatus", () => {
  const makeDetail = (overrides: Partial<WatchQueryDetailResponse> = {}): WatchQueryDetailResponse => ({
    id: 1,
    name: "Test",
    threshold_cents: 40000,
    is_active: true,
    schedule: "daily",
    retailer_urls: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  });

  it("returns paused when detail.is_active is false", () => {
    const detail = makeDetail({ is_active: false });
    expect(deriveStatus(detail, false)).toBe("paused");
  });

  it("returns running when isScrapingLocal is true", () => {
    const detail = makeDetail({ is_active: true });
    expect(deriveStatus(detail, true)).toBe("running");
  });

  it("returns ok when detail is undefined", () => {
    expect(deriveStatus(undefined, false)).toBe("ok");
  });

  it("returns ok for active query with successful scrapes", () => {
    const detail = makeDetail({
      is_active: true,
      retailer_urls: [
        {
          id: 1,
          url: "https://example.com",
          created_at: "2026-01-01T00:00:00Z",
          latest_result: {
            product_name: "Test",
            price_cents: 35000,
            listing_url: "https://example.com",
            scraped_at: "2026-01-01T00:00:00Z",
            direction: "new",
            delta_cents: 0,
            pct_change: 0,
          },
        },
      ],
    });
    expect(deriveStatus(detail, false)).toBe("ok");
  });
});
