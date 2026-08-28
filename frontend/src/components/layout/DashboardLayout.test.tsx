import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import DashboardLayout from "./DashboardLayout";

vi.mock("./Sidebar", () => {
  return {
    default: ({ isOpen, onClose }: any) => (
      <div data-testid="sidebar">
        <span>{isOpen ? "Sidebar Open" : "Sidebar Closed"}</span>
        <button data-testid="close-sidebar" onClick={onClose}>
          Close Sidebar
        </button>
      </div>
    ),
  };
});

describe("DashboardLayout", () => {
  const mockCurrentUser = {
    id: "1",
    email: "test@test.com",
    full_name: "Test User",
    role: "user" as any,
    is_active: true,
  };

  const mockOnLogout = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders children correctly", () => {
    render(
      <DashboardLayout currentUser={mockCurrentUser} onLogout={mockOnLogout}>
        <div data-testid="child-content">Child Content</div>
      </DashboardLayout>,
    );

    expect(screen.getByTestId("child-content")).toBeInTheDocument();
  });

  it("opens and closes the mobile sidebar", () => {
    render(
      <DashboardLayout currentUser={mockCurrentUser} onLogout={mockOnLogout}>
        <div>Content</div>
      </DashboardLayout>,
    );

    expect(screen.getByText("Sidebar Closed")).toBeInTheDocument();

    const menuButtons = screen.getAllByRole("button");
    const mobileMenuButton = menuButtons.find((b) =>
      b.className.includes("-ml-2"),
    );

    if (mobileMenuButton) {
      fireEvent.click(mobileMenuButton);
    }

    expect(screen.getByText("Sidebar Open")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("close-sidebar"));
    expect(screen.getByText("Sidebar Closed")).toBeInTheDocument();
  });
});
