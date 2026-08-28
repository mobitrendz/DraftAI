import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import React from "react";
import ErrorBoundary from "./ErrorBoundary";

describe("ErrorBoundary", () => {
  const ProblemChild = () => {
    throw new Error("Test error!");
  };

  it("renders children when there is no error", () => {
    render(
      <ErrorBoundary>
        <div data-testid="child">Happy Child</div>
      </ErrorBoundary>,
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("renders fallback UI when there is an error", () => {
    // Suppress console.error for this test to avoid noisy test output
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Application Crash")).toBeInTheDocument();
    expect(screen.getByText("Error: Test error!")).toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it("reloads page when refresh button is clicked", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    // Mock window.location.reload
    const originalLocation = window.location;
    const reloadMock = vi.fn();
    vi.stubGlobal("location", {
      ...originalLocation,
      reload: reloadMock,
    });

    render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>,
    );

    const btn = screen.getByText("Refresh Application");
    fireEvent.click(btn);

    expect(reloadMock).toHaveBeenCalled();

    // Restore window.location
    vi.unstubAllGlobals();
    consoleSpy.mockRestore();
  });
});
