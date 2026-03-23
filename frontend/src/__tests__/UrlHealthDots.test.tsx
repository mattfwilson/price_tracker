import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { UrlHealthDots } from "@/components/dashboard/UrlHealthDots";
import type { UrlHealthResponse } from "@/types/api";

const makeHealth = (
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

const HEALTH_DATA: UrlHealthResponse[] = [
  makeHealth({
    retailer_url_id: 1,
    domain: "amazon.com",
    status: "healthy",
    success_count: 9,
    window_size: 10,
    last_success_at: "2026-03-20T10:00:00Z",
  }),
  makeHealth({
    retailer_url_id: 2,
    domain: "bestbuy.com",
    status: "degraded",
    success_count: 6,
    window_size: 10,
    last_success_at: "2026-03-19T10:00:00Z",
    consecutive_failures: 2,
    last_error_type: "blocked",
  }),
  makeHealth({
    retailer_url_id: 3,
    domain: "walmart.com",
    status: "failing",
    success_count: 3,
    window_size: 10,
    last_success_at: null,
    consecutive_failures: 5,
    last_error_type: "timeout",
  }),
];

describe("UrlHealthDots", () => {
  it("renders one dot row per URL in health data", () => {
    const { container } = render(<UrlHealthDots healthData={HEALTH_DATA} />);
    // Three domain labels should be present
    expect(screen.getByText("amazon.com")).toBeInTheDocument();
    expect(screen.getByText("bestbuy.com")).toBeInTheDocument();
    expect(screen.getByText("walmart.com")).toBeInTheDocument();
    // Each domain label uses text-xs text-muted-foreground
    const labels = container.querySelectorAll(".text-xs.text-muted-foreground");
    expect(labels.length).toBeGreaterThanOrEqual(3);
  });

  it("renders green dot (bg-emerald-500) for healthy status", () => {
    const { container } = render(
      <UrlHealthDots healthData={[makeHealth({ status: "healthy" })]} />
    );
    const dot = container.querySelector(".bg-emerald-500");
    expect(dot).toBeInTheDocument();
  });

  it("renders amber dot (bg-amber-500) for degraded status", () => {
    const { container } = render(
      <UrlHealthDots healthData={[makeHealth({ status: "degraded" })]} />
    );
    const dot = container.querySelector(".bg-amber-500");
    expect(dot).toBeInTheDocument();
  });

  it("renders red dot (bg-red-500) for failing status", () => {
    const { container } = render(
      <UrlHealthDots healthData={[makeHealth({ status: "failing" })]} />
    );
    const dot = container.querySelector(".bg-red-500");
    expect(dot).toBeInTheDocument();
  });

  it("renders domain label text for each URL", () => {
    render(<UrlHealthDots healthData={HEALTH_DATA} />);
    expect(screen.getByText("amazon.com")).toBeInTheDocument();
    expect(screen.getByText("bestbuy.com")).toBeInTheDocument();
    expect(screen.getByText("walmart.com")).toBeInTheDocument();
  });

  it("renders title attribute with domain, success rate, and last success time", () => {
    const { container } = render(
      <UrlHealthDots
        healthData={[
          makeHealth({
            domain: "amazon.com",
            success_count: 9,
            window_size: 10,
            last_success_at: "2026-03-20T10:00:00Z",
          }),
        ]}
      />
    );
    const row = container.querySelector("[title]");
    expect(row).not.toBeNull();
    const title = row!.getAttribute("title")!;
    expect(title).toContain("amazon.com");
    expect(title).toContain("9/10");
    expect(title).toContain("last success");
  });

  it("renders title with 'never' when last_success_at is null", () => {
    const { container } = render(
      <UrlHealthDots
        healthData={[
          makeHealth({
            domain: "walmart.com",
            last_success_at: null,
          }),
        ]}
      />
    );
    const row = container.querySelector("[title]");
    expect(row).not.toBeNull();
    const title = row!.getAttribute("title")!;
    expect(title).toContain("last success never");
  });

  it("renders nothing when healthData is undefined", () => {
    const { container } = render(<UrlHealthDots healthData={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when healthData is empty array", () => {
    const { container } = render(<UrlHealthDots healthData={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
