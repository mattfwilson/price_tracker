import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("recharts", () => {
  const ResponsiveContainer = ({ children, ...props }: any) => (
    <div data-testid="responsive-container" {...props}>
      {children}
    </div>
  );
  const LineChart = ({ children, ...props }: any) => (
    <div data-testid="line-chart" data-data={JSON.stringify(props.data)}>
      {children}
    </div>
  );
  const Line = (props: any) => (
    <div data-testid="line" data-datakey={props.dataKey} />
  );
  const XAxis = (props: any) => (
    <div data-testid="x-axis" data-datakey={props.dataKey} />
  );
  const YAxis = (props: any) => <div data-testid="y-axis" />;
  const Tooltip = (props: any) => <div data-testid="tooltip" />;
  const ReferenceLine = (props: any) => (
    <div data-testid="reference-line" y={String(props.y)} />
  );
  const CartesianGrid = (props: any) => (
    <div data-testid="cartesian-grid" />
  );

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

import { PriceChart } from "@/components/history/PriceChart";

const sampleData = [
  { date: "Mar 1", price: 49.99, scraped_at: "2026-03-01T00:00:00Z" },
  { date: "Mar 5", price: 47.5, scraped_at: "2026-03-05T00:00:00Z" },
  { date: "Mar 10", price: 45.0, scraped_at: "2026-03-10T00:00:00Z" },
];

describe("PriceChart", () => {
  it("renders chart container", () => {
    render(<PriceChart data={sampleData} thresholdDollars={50} />);
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("renders threshold reference line when thresholdDollars provided", () => {
    render(<PriceChart data={sampleData} thresholdDollars={50} />);
    const refLine = screen.getByTestId("reference-line");
    expect(refLine).toBeInTheDocument();
    expect(refLine).toHaveAttribute("y", "50");
  });

  it("does not render threshold line when thresholdDollars is null", () => {
    render(<PriceChart data={sampleData} thresholdDollars={null} />);
    expect(screen.queryByTestId("reference-line")).toBeNull();
  });
});
