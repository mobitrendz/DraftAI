import { render, screen, fireEvent, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeContext";

const ThemeTestComponent = () => {
  const { theme, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="current-theme">{theme}</span>
      <button onClick={() => setTheme("light")}>Set Light</button>
      <button onClick={() => setTheme("dark")}>Set Dark</button>
      <button onClick={() => setTheme("system")}>Set System</button>
    </div>
  );
};

describe("ThemeContext", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();

    // Mock matchMedia
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query) => ({
        matches: query === "(prefers-color-scheme: dark)",
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it("provides default theme", () => {
    render(
      <ThemeProvider defaultTheme="light" storageKey="test-theme">
        <ThemeTestComponent />
      </ThemeProvider>,
    );
    expect(screen.getByTestId("current-theme").textContent).toBe("light");
  });

  it("switches theme and persists in localStorage", () => {
    render(
      <ThemeProvider defaultTheme="light" storageKey="test-theme">
        <ThemeTestComponent />
      </ThemeProvider>,
    );

    fireEvent.click(screen.getByText("Set Dark"));
    expect(screen.getByTestId("current-theme").textContent).toBe("dark");
    expect(window.localStorage.getItem("test-theme")).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("handles system theme preference", () => {
    render(
      <ThemeProvider defaultTheme="light" storageKey="test-theme">
        <ThemeTestComponent />
      </ThemeProvider>,
    );

    fireEvent.click(screen.getByText("Set System"));
    expect(screen.getByTestId("current-theme").textContent).toBe("system");
    // Since matchMedia mock returns true for dark:
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("loads theme from localStorage on mount", () => {
    window.localStorage.setItem("test-theme", "dark");
    render(
      <ThemeProvider defaultTheme="light" storageKey="test-theme">
        <ThemeTestComponent />
      </ThemeProvider>,
    );
    expect(screen.getByTestId("current-theme").textContent).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("returns default theme when useTheme is used outside provider", () => {
    render(<ThemeTestComponent />);
    expect(screen.getByTestId("current-theme").textContent).toBe("system");
  });

  it("returns default theme when useTheme is used outside provider", () => {
    render(<ThemeTestComponent />);
    expect(screen.getByTestId("current-theme").textContent).toBe("system");
  });
});
