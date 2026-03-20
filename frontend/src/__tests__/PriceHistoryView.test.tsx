import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { HistoryRecord } from "@/types/api";

const mockRefetch = vi.fn();

vi.mock("@/hooks/use-watch-queries", () => ({
  useListingHistory: vi.fn(),
}));

vi.mock("recharts", () => {
  const ResponsiveContainer = ({ children, ...props }: any) => (
    <div data-testid="responsive-container" {...props}>
      {children}
    </div>
  );
  const LineChart = ({ children }: any) => (
    <div data-testid="line-chart">{children}</div>
  );
  const Line = () => <div data-testid="line" />;
  const XAxis = () => <div data-testid="x-axis" />;
  const YAxis = () => <div data-testid="y-axis" />;
  const Tooltip = () => <div data-testid="tooltip" />;
  const ReferenceLine = () => <div data-testid="reference-line" />;
  const CartesianGrid = () => <div data-testid="cartesian-grid" />;

  return {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    ReferenceLine,
    CartesianGrid,
  };
});

import { PriceHistoryView } from "@/components/history/PriceHistoryView";
import { useListingHistory } from "@/hooks/use-watch-queries";

const mockedUseListingHistory = vi.mocked(useListingHistory);

const sampleRecords: HistoryRecord[] = [
  {
    id: 1,
    product_name: "Widget",
    price_cents: 5000,
    retailer_name: "Amazon",
    listing_url: "https://amazon.com/widget",
    scraped_at: "2026-03-01T12:00:00Z",
    direction: "new",
    delta_cents: 0,
    pct_change: 0,
  },
  {
    id: 2,
    product_name: "Widget",
    price_cents: 4800,
    retailer_name: "Amazon",
    listing_url: "https://amazon.com/widget",
    scraped_at: "2026-03-10T12:00:00Z",
    direction: "lower",
    delta_cents: -200,
    pct_change: -4.0,
  },
];

const defaultProps = {
  retailerUrlId: 1,
  thresholdCents: 5500,
  productName: "Widget",
  retailerDomain: "amazon.com",
  onBack: vi.fn(),
};

describe("PriceHistoryView", () => {
  it("shows loading skeleton while fetching", () => {
    mockedUseListingHistory.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: mockRefetch,
    } as any);

    render(<PriceHistoryView {...defaultProps} />);
    // Skeleton elements use animate-pulse class
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows empty state when no records", () => {
    mockedUseListingHistory.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: mockRefetch,
    } as any);

    render(<PriceHistoryView {...defaultProps} />);
    expect(screen.getByText("No history yet")).toBeInTheDocument();
  });

  it("shows error state with retry button", () => {
    mockedUseListingHistory.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      refetch: mockRefetch,
    } as any);

    render(<PriceHistoryView {...defaultProps} />);
    expect(screen.getByText("Couldn't load history")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("renders chart and table when data loaded", () => {
    mockedUseListingHistory.mockReturnValue({
      data: sampleRecords,
      isLoading: false,
      isError: false,
      refetch: mockRefetch,
    } as any);

    render(<PriceHistoryView {...defaultProps} />);
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    // Table should have rows
    const rows = screen.getAllByRole("row");
    expect(rows.length).toBeGreaterThan(1);
  });

  it("time range filter defaults to 30d", () => {
    mockedUseListingHistory.mockReturnValue({
      data: sampleRecords,
      isLoading: false,
      isError: false,
      refetch: mockRefetch,
    } as any);

    render(<PriceHistoryView {...defaultProps} />);
    const btn30d = screen.getByText("30d");
    expect(btn30d).toHaveClass("bg-primary");
  });
});
