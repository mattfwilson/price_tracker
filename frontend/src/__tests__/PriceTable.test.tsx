import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PriceTable } from "@/components/history/PriceTable";
import type { HistoryRecord } from "@/types/api";

const sampleData: HistoryRecord[] = [
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
    scraped_at: "2026-03-05T12:00:00Z",
    direction: "lower",
    delta_cents: -200,
    pct_change: -4.0,
  },
  {
    id: 3,
    product_name: "Widget",
    price_cents: 5200,
    retailer_name: "Amazon",
    listing_url: "https://amazon.com/widget",
    scraped_at: "2026-03-10T12:00:00Z",
    direction: "higher",
    delta_cents: 400,
    pct_change: 8.3,
  },
];

describe("PriceTable", () => {
  it("renders table with 3 data rows", () => {
    render(<PriceTable data={sampleData} />);
    const rows = screen.getAllByRole("row");
    // 1 header row + 3 data rows
    expect(rows).toHaveLength(4);
  });

  it("default sort is newest-first", () => {
    render(<PriceTable data={sampleData} />);
    const rows = screen.getAllByRole("row");
    // First data row (index 1) should be the newest: Mar 10
    expect(rows[1]).toHaveTextContent("$52.00");
  });

  it("clicking Date header toggles sort direction", async () => {
    const user = userEvent.setup();
    render(<PriceTable data={sampleData} />);

    const dateHeader = screen.getByText("Date", { selector: "th" });
    await user.click(dateHeader);

    // Now oldest-first: Mar 1
    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("$50.00");
  });

  it("clicking Price header sorts by price", async () => {
    const user = userEvent.setup();
    render(<PriceTable data={sampleData} />);

    const priceHeader = screen.getByText("Price", { selector: "th" });
    await user.click(priceHeader);

    // Ascending by price: $48.00 first
    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("$48.00");
  });

  it("displays delta with correct color class", () => {
    render(<PriceTable data={sampleData} />);
    const lowerDelta = screen.getByText(/4\.0%/);
    expect(lowerDelta.closest("span")).toHaveClass("text-emerald-400");
  });
});
