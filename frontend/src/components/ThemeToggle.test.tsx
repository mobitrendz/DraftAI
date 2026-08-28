import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { ThemeToggle, ThemeToggleCompact } from "./ThemeToggle";
import { useTheme } from "../contexts/ThemeContext";

vi.mock("../contexts/ThemeContext", () => ({
  useTheme: vi.fn(),
}));

describe("ThemeToggle", () => {
  const setThemeMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useTheme as any).mockReturnValue({
      theme: "light",
      setTheme: setThemeMock,
    });
  });

  it("renders all theme options in full view", () => {
    render(<ThemeToggle />);
    // Check for light, dark, system icons (Lucide icons render as SVG)
    expect(screen.getAllByRole("button")).toHaveLength(3);
  });

  it("calls setTheme with correct value when clicked", () => {
    render(<ThemeToggle />);
    const buttons = screen.getAllByRole("button");

    fireEvent.click(buttons[1]); // dark
    expect(setThemeMock).toHaveBeenCalledWith("dark");

    fireEvent.click(buttons[2]); // system
    expect(setThemeMock).toHaveBeenCalledWith("system");
  });

  it("ThemeToggleCompact toggles between light and dark", () => {
    render(<ThemeToggleCompact />);
    const button = screen.getByRole("button");

    fireEvent.click(button);
    expect(setThemeMock).toHaveBeenCalledWith("dark"); // because initial is light
  });

  it("ThemeToggleCompact toggles to light if current is dark", () => {
    (useTheme as any).mockReturnValue({
      theme: "dark",
      setTheme: setThemeMock,
    });

    render(<ThemeToggleCompact />);
    const button = screen.getByRole("button");

    fireEvent.click(button);
    expect(setThemeMock).toHaveBeenCalledWith("light");
  });
});
