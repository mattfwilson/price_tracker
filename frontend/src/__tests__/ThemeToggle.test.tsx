import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useTheme } from "next-themes";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

vi.mock("next-themes", () => ({
  useTheme: vi.fn(),
}));

const mockUseTheme = useTheme as ReturnType<typeof vi.fn>;

describe("ThemeToggle", () => {
  const mockSetTheme = vi.fn();

  beforeEach(() => {
    mockSetTheme.mockClear();
  });

  it("renders toggle button with aria-label", () => {
    mockUseTheme.mockReturnValue({ theme: "dark", setTheme: mockSetTheme });
    render(<ThemeToggle />);
    expect(screen.getByRole("button", { name: /toggle theme/i })).toBeInTheDocument();
  });

  it("calls setTheme with 'light' when current theme is dark", () => {
    mockUseTheme.mockReturnValue({ theme: "dark", setTheme: mockSetTheme });
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: /toggle theme/i }));
    expect(mockSetTheme).toHaveBeenCalledWith("light");
  });

  it("calls setTheme with 'dark' when current theme is light", () => {
    mockUseTheme.mockReturnValue({ theme: "light", setTheme: mockSetTheme });
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: /toggle theme/i }));
    expect(mockSetTheme).toHaveBeenCalledWith("dark");
  });
});
