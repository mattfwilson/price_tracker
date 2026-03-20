import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AlertsPage } from "@/pages/AlertsPage";

let mockAlerts: Array<{
  id: number;
  watch_query_id: number;
  watch_query_name: string;
  product_name: string;
  price_cents: number;
  retailer_name: string;
  listing_url: string;
  is_read: boolean;
  created_at: string;
}> = [];
let mockIsLoading = false;

vi.mock("@/hooks/use-alerts", () => ({
  useAlerts: () => ({
    data: mockAlerts,
    isLoading: mockIsLoading,
    isError: false,
  }),
  useMarkAlertRead: () => ({ mutate: vi.fn() }),
  useDismissAllAlerts: () => ({ mutate: vi.fn(), isPending: false }),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <AlertsPage />
    </MemoryRouter>
  );
}

describe("AlertsPage", () => {
  it("renders Alert Log heading", () => {
    mockAlerts = [];
    mockIsLoading = false;
    renderPage();
    expect(screen.getByText("Alert Log")).toBeInTheDocument();
  });

  it("renders Dismiss All button when alerts exist", () => {
    mockAlerts = [
      {
        id: 1,
        watch_query_id: 1,
        watch_query_name: "MacBook Pro",
        product_name: "MacBook Pro 16",
        price_cents: 34999,
        retailer_name: "Amazon",
        listing_url: "https://amazon.com/macbook",
        is_read: false,
        created_at: new Date().toISOString(),
      },
    ];
    mockIsLoading = false;
    renderPage();
    expect(screen.getByRole("button", { name: "Dismiss All" })).toBeInTheDocument();
  });

  it("renders empty state when no alerts", () => {
    mockAlerts = [];
    mockIsLoading = false;
    renderPage();
    expect(screen.getByText("No alerts yet")).toBeInTheDocument();
  });

  it("renders alert rows with query name and price when alerts exist", () => {
    mockAlerts = [
      {
        id: 1,
        watch_query_id: 1,
        watch_query_name: "MacBook Pro",
        product_name: "MacBook Pro 16",
        price_cents: 34999,
        retailer_name: "Amazon",
        listing_url: "https://amazon.com/macbook",
        is_read: false,
        created_at: new Date().toISOString(),
      },
    ];
    mockIsLoading = false;
    renderPage();
    expect(screen.getByText("MacBook Pro")).toBeInTheDocument();
    expect(screen.getByText("$349.99")).toBeInTheDocument();
  });
});
