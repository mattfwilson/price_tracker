import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { BellDropdown } from "@/components/alerts/BellDropdown";

let mockUnreadCount = 0;
const mockAlerts: Array<{
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

vi.mock("@/hooks/use-alerts", () => ({
  useAlerts: () => ({
    data: mockAlerts,
    isLoading: false,
    isError: false,
  }),
  useUnreadCount: () => ({
    data: { unread_count: mockUnreadCount },
  }),
  useMarkAlertRead: () => ({ mutate: vi.fn() }),
  useDismissAllAlerts: () => ({ mutate: vi.fn(), isPending: false }),
}));

function renderBell() {
  return render(
    <MemoryRouter>
      <BellDropdown />
    </MemoryRouter>
  );
}

describe("BellDropdown", () => {
  it("renders bell icon", () => {
    mockUnreadCount = 0;
    renderBell();
    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
  });

  it("shows badge with count when unreadCount > 0", () => {
    mockUnreadCount = 3;
    renderBell();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("hides badge when unreadCount is 0", () => {
    mockUnreadCount = 0;
    renderBell();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("renders alerts header text with unread count in popover", async () => {
    mockUnreadCount = 3;
    mockAlerts.length = 0;
    mockAlerts.push({
      id: 1,
      watch_query_id: 1,
      watch_query_name: "MacBook Pro",
      product_name: "MacBook Pro 16",
      price_cents: 34999,
      retailer_name: "Amazon",
      listing_url: "https://amazon.com/macbook",
      is_read: false,
      created_at: new Date().toISOString(),
    });
    renderBell();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(screen.getByText("Alerts (3 unread)")).toBeInTheDocument();
    });
  });
});
