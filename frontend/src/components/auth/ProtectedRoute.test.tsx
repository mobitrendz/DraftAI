import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import React from "react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import { useAuth, Role } from "../../contexts/AuthContext";

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  Role: {
    SUPER: "SUPER",
    ADMIN: "ADMIN",
    USER: "USER",
  },
}));

describe("ProtectedRoute", () => {
  it("shows loading spinner when isLoading is true", () => {
    (useAuth as any).mockReturnValue({
      isLoading: true,
      isAuthenticated: false,
    });

    const { container } = render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("redirects to login when not authenticated", () => {
    (useAuth as any).mockReturnValue({
      isLoading: false,
      isAuthenticated: false,
    });

    render(
      <MemoryRouter initialEntries={["/protected"]}>
        <Routes>
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Login Page")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders children when authenticated and no specific role required", () => {
    (useAuth as any).mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
    });

    render(
      <MemoryRouter>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });

  it("renders Access Denied when user lacks required role", () => {
    (useAuth as any).mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
      hasPermission: vi.fn().mockReturnValue(false),
    });

    render(
      <MemoryRouter>
        <ProtectedRoute requiredRole={Role.ADMIN}>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    expect(screen.getByText("Access Denied")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders children when user has required role", () => {
    (useAuth as any).mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
      hasPermission: vi.fn().mockReturnValue(true),
    });

    render(
      <MemoryRouter>
        <ProtectedRoute requiredRole={Role.ADMIN}>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>,
    );

    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });
});
