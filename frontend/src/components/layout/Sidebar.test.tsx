import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Sidebar from "./Sidebar";
import { useAuth } from "../../contexts/AuthContext";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  Role: {
    SUPER: "SUPER",
    ADMIN: "ADMIN",
    USER: "USER",
  },
}));

describe("Sidebar", () => {
  const mockOnLogout = vi.fn();
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as any).mockReturnValue({
      hasPermission: vi.fn().mockReturnValue(true),
    });
  });

  const renderSidebar = (props = {}) => {
    return render(
      <MemoryRouter>
        <Sidebar
          userRole="user"
          userName="Test User"
          onLogout={mockOnLogout}
          isOpen={true}
          onClose={mockOnClose}
          {...props}
        />
      </MemoryRouter>,
    );
  };

  it("renders correctly with user details", () => {
    renderSidebar();
    expect(screen.getByText("Test User")).toBeInTheDocument();
    expect(screen.getByText("user")).toBeInTheDocument();
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("calls onClose when mobile overlay is clicked", () => {
    renderSidebar();
    const overlay = document.querySelector(".fixed.inset-0.bg-black\\/50");
    if (overlay) fireEvent.click(overlay);
    expect(mockOnClose).toHaveBeenCalled();
  });

  it("calls onLogout when Sign Out is clicked", () => {
    renderSidebar();
    fireEvent.click(screen.getByText("Sign Out"));
    expect(mockOnLogout).toHaveBeenCalled();
  });
});
