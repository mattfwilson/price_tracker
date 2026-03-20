import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryFormDialog } from "@/components/query/QueryFormDialog";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { WatchQueryDetailResponse } from "@/types/api";

const mockCreateMutateAsync = vi.fn();
const mockUpdateMutateAsync = vi.fn();

vi.mock("@/hooks/use-watch-queries", () => ({
  useCreateWatchQuery: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useUpdateWatchQuery: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
  useDeleteWatchQuery: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

const editQuery: WatchQueryDetailResponse = {
  id: 1,
  name: "MacBook Pro",
  threshold_cents: 150000,
  is_active: true,
  schedule: "daily",
  retailer_urls: [
    {
      id: 10,
      url: "https://www.amazon.com/macbook",
      created_at: "2026-01-01T00:00:00Z",
      latest_result: null,
    },
  ],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderDialog(props: Partial<Parameters<typeof QueryFormDialog>[0]> = {}) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <QueryFormDialog open={true} onOpenChange={vi.fn()} {...props} />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  mockCreateMutateAsync.mockReset();
  mockUpdateMutateAsync.mockReset();
});

describe("QueryFormDialog", () => {
  it("renders 'Create Query' title when no editQuery provided", () => {
    renderDialog();
    expect(screen.getByText("Create Query", { selector: "[class*='font-heading']" })).toBeInTheDocument();
  });

  it("renders 'Edit Query' title when editQuery provided", () => {
    renderDialog({ editQuery });
    expect(screen.getByText("Edit Query")).toBeInTheDocument();
  });

  it("renders 'Save Changes' button text when editing", () => {
    renderDialog({ editQuery });
    expect(screen.getByRole("button", { name: /Save Changes/ })).toBeInTheDocument();
  });

  it("renders 'Create Query' button text when creating", () => {
    renderDialog();
    expect(screen.getByRole("button", { name: /Create Query/ })).toBeInTheDocument();
  });

  it("validates empty name shows 'Query name is required' error", async () => {
    renderDialog();
    const submitBtn = screen.getByRole("button", { name: /Create Query/ });
    fireEvent.click(submitBtn);
    expect(await screen.findByText("Query name is required")).toBeInTheDocument();
  });

  it("validates threshold format shows error for non-numeric input", async () => {
    renderDialog();
    const nameInput = screen.getByPlaceholderText("e.g. MacBook Pro 16");
    await userEvent.type(nameInput, "Test Query");

    const thresholdInput = screen.getByPlaceholderText("400.00");
    await userEvent.type(thresholdInput, "abc");

    const urlInput = screen.getByPlaceholderText("https://www.example.com/product");
    await userEvent.type(urlInput, "https://example.com");

    const submitBtn = screen.getByRole("button", { name: /Create Query/ });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText("Enter a valid dollar amount (e.g. 400.00)")
    ).toBeInTheDocument();
  });

  it("validates at least one URL required", async () => {
    renderDialog();
    const nameInput = screen.getByPlaceholderText("e.g. MacBook Pro 16");
    await userEvent.type(nameInput, "Test Query");

    const thresholdInput = screen.getByPlaceholderText("400.00");
    await userEvent.type(thresholdInput, "400.00");

    // Clear the default empty URL field - it's already empty
    const submitBtn = screen.getByRole("button", { name: /Create Query/ });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText("At least one retailer URL is required")
    ).toBeInTheDocument();
  });

  it("dollar-to-cents conversion sends correct threshold_cents", async () => {
    mockCreateMutateAsync.mockResolvedValue({});
    renderDialog();

    const nameInput = screen.getByPlaceholderText("e.g. MacBook Pro 16");
    await userEvent.type(nameInput, "Test Query");

    const thresholdInput = screen.getByPlaceholderText("400.00");
    await userEvent.type(thresholdInput, "400.50");

    const urlInput = screen.getByPlaceholderText("https://www.example.com/product");
    await userEvent.type(urlInput, "https://www.amazon.com/product");

    const submitBtn = screen.getByRole("button", { name: /Create Query/ });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockCreateMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          threshold_cents: 40050,
        })
      );
    });
  });
});
