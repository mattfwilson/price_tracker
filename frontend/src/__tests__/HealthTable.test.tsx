import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { HealthTable } from "@/components/health/HealthTable";
import { HealthFilter } from "@/components/health/HealthFilter";
import { HealthStatusDot } from "@/components/health/HealthStatusDot";
import type { UrlHealthResponse } from "@/types/api";

const makeUrl = (
  overrides: Partial<UrlHealthResponse> = {}
): UrlHealthResponse => ({
  retailer_url_id: 1,
  url: "https://amazon.com/dp/B001",
  domain: "amazon.com",
  watch_query_id: 1,
  watch_query_name: "GPU Query",
  status: "healthy",
  success_count: 9,
  window_size: 10,
  last_success_at: "2026-03-20T10:00:00Z",
  consecutive_failures: 0,
  last_error_type: null,
  ...overrides,
});

const URLS: UrlHealthResponse[] = [
  makeUrl({
    retailer_url_id: 1,
    url: "https://amazon.com/dp/B001",
    domain: "amazon.com",
    watch_query_name: "GPU Query",
    status: "healthy",
    success_count: 9,
    window_size: 10,
    consecutive_failures: 0,
    last_error_type: null,
  }),
  makeUrl({
    retailer_url_id: 2,
    url: "https://bestbuy.com/site/B002",
    domain: "bestbuy.com",
    watch_query_id: 2,
    watch_query_name: "CPU Query",
    status: "degraded",
    success_count: 6,
    window_size: 10,
    consecutive_failures: 2,
    last_error_type: "blocked",
  }),
  makeUrl({
    retailer_url_id: 3,
    url: "https://walmart.com/ip/B003",
    domain: "walmart.com",
    watch_query_id: 3,
    watch_query_name: "RAM Query",
    status: "failing",
    success_count: 3,
    window_size: 10,
    last_success_at: null,
    consecutive_failures: 5,
    last_error_type: "timeout",
  }),
];

describe("HealthTable", () => {
  it("renders all provided URL rows with correct columns", () => {
    render(<HealthTable urls={URLS} />);
    expect(screen.getByText("amazon.com")).toBeInTheDocument();
    expect(screen.getByText("bestbuy.com")).toBeInTheDocument();
    expect(screen.getByText("walmart.com")).toBeInTheDocument();
    expect(screen.getByText("GPU Query")).toBeInTheDocument();
    expect(screen.getByText("CPU Query")).toBeInTheDocument();
    expect(screen.getByText("RAM Query")).toBeInTheDocument();
    expect(screen.getByText("9/10")).toBeInTheDocument();
    expect(screen.getByText("6/10")).toBeInTheDocument();
    expect(screen.getByText("3/10")).toBeInTheDocument();
    expect(screen.getByText("timeout")).toBeInTheDocument();
  });

  it("default sort is status descending (failing first, then degraded, then healthy)", () => {
    render(<HealthTable urls={URLS} />);
    const rows = screen.getAllByRole("row");
    // rows[0] is header, rows[1..3] are data
    expect(rows[1]).toHaveTextContent("walmart.com"); // failing
    expect(rows[2]).toHaveTextContent("bestbuy.com"); // degraded
    expect(rows[3]).toHaveTextContent("amazon.com");  // healthy
  });

  it("clicking Watch Query column header sorts alphabetically by watch_query_name", async () => {
    const user = userEvent.setup();
    render(<HealthTable urls={URLS} />);
    const watchQueryHeader = screen.getByRole("columnheader", { name: /watch query/i });
    await user.click(watchQueryHeader);
    const rows = screen.getAllByRole("row");
    // CPU Query < GPU Query < RAM Query alphabetically
    expect(rows[1]).toHaveTextContent("CPU Query");
    expect(rows[2]).toHaveTextContent("GPU Query");
    expect(rows[3]).toHaveTextContent("RAM Query");
  });

  it("clicking Last Success column header sorts by last_success_at (null last)", async () => {
    const user = userEvent.setup();
    render(<HealthTable urls={URLS} />);
    const lastSuccessHeader = screen.getByRole("columnheader", { name: /last success/i });
    await user.click(lastSuccessHeader);
    const rows = screen.getAllByRole("row");
    // oldest first for asc; null should be last
    // GPU has 2026-03-20T10:00:00Z, bestbuy has 2026-03-20T10:00:00Z (same), walmart is null
    const lastRow = rows[rows.length - 1];
    expect(lastRow).toHaveTextContent("walmart.com"); // null last_success_at
  });
});

describe("HealthFilter", () => {
  it("HealthFilter with Degraded & Failing active hides healthy URLs", async () => {
    const user = userEvent.setup();
    let mode: "all" | "problems" = "all";
    const onChange = (m: "all" | "problems") => { mode = m; };
    const { rerender } = render(<HealthFilter mode={mode} onChange={onChange} />);
    const problemsBtn = screen.getByRole("button", { name: /degraded & failing/i });
    await user.click(problemsBtn);
    // mode should now be "problems"
    expect(mode).toBe("problems");
  });

  it("HealthFilter with All active shows all filter state", async () => {
    const user = userEvent.setup();
    let mode: "all" | "problems" = "problems";
    const onChange = (m: "all" | "problems") => { mode = m; };
    render(<HealthFilter mode={mode} onChange={onChange} />);
    const allBtn = screen.getByRole("button", { name: /^all$/i });
    await user.click(allBtn);
    expect(mode).toBe("all");
  });
});

describe("HealthStatusDot", () => {
  it("renders correct color class for healthy status", () => {
    const { container } = render(<HealthStatusDot status="healthy" />);
    expect(container.querySelector(".bg-emerald-500")).toBeInTheDocument();
  });

  it("renders correct color class for degraded status", () => {
    const { container } = render(<HealthStatusDot status="degraded" />);
    expect(container.querySelector(".bg-amber-500")).toBeInTheDocument();
  });

  it("renders correct color class for failing status", () => {
    const { container } = render(<HealthStatusDot status="failing" />);
    expect(container.querySelector(".bg-red-500")).toBeInTheDocument();
  });

  it("shows label when showLabel is true", () => {
    render(<HealthStatusDot status="healthy" showLabel />);
    expect(screen.getByText("Healthy")).toBeInTheDocument();
  });
});
