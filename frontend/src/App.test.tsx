import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
import { useAuth, Role } from "./contexts/AuthContext";

vi.mock("./lib/auth", () => ({
  auth: {
    initialize: vi.fn(),
    isAuthenticated: vi.fn(),
    clearToken: vi.fn(),
    getToken: vi.fn(),
    setToken: vi.fn(),
  },
}));

vi.mock("./contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  Role: {
    SUPER: "SUPER",
    ADMIN: "ADMIN",
    USER: "USER",
  },
  AuthProvider: ({ children }: any) => <div>{children}</div>,
}));

// Mock BrowserRouter to use MemoryRouter internally for tests
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    BrowserRouter: ({ children }: any) => <div>{children}</div>,
  };
});

// Mock components to simplify
vi.mock("./components/Login", () => ({
  default: () => {
    const { login } = useAuth();
    return (
      <div>
        Login Page
        <button onClick={() => login("token")}>Mock Login</button>
      </div>
    );
  },
}));

vi.mock("./components/Dashboard", () => ({
  default: () => {
    const { logout } = useAuth();
    return (
      <div>
        Dashboard Page
        <button onClick={logout}>Mock Logout</button>
      </div>
    );
  },
}));

vi.mock("./components/Profile", () => ({
  default: () => <div>Profile Page</div>,
}));

vi.mock("./components/SettingsPage", () => ({
  default: () => <div>Settings Page</div>,
}));

describe("App Component", () => {
  let authState = {
    isAuthenticated: false,
    user: null as any,
    role: null as any,
  };

  const mockLogin = vi.fn((token: string) => {
    authState.isAuthenticated = true;
    authState.user = {
      id: "1",
      email: "t@t.com",
      role: "USER",
      is_active: true,
    };
    authState.role = Role.USER;
  });

  const mockLogout = vi.fn(() => {
    authState.isAuthenticated = false;
    authState.user = null;
    authState.role = null;
  });

  beforeEach(() => {
    vi.clearAllMocks();
    authState = {
      isAuthenticated: false,
      user: null,
      role: null,
    };

    vi.mocked(useAuth).mockImplementation(() => ({
      isAuthenticated: authState.isAuthenticated,
      isLoading: false,
      user: authState.user,
      role: authState.role,
      login: mockLogin,
      logout: mockLogout,
      hasPermission: vi.fn(
        (r) =>
          !authState.role ||
          r === authState.role ||
          authState.role === Role.SUPER ||
          authState.role === Role.ADMIN,
      ),
      accessDenied: false,
      setAccessDenied: vi.fn(),
      token: authState.isAuthenticated ? "fake-token" : null,
    }));
  });

  it("renders login page when not authenticated", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("renders dashboard when authenticated", async () => {
    authState.isAuthenticated = true;
    authState.user = {
      id: "1",
      email: "t@t.com",
      role: "USER",
      is_active: true,
    };
    authState.role = Role.USER;

    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Dashboard Page")).toBeInTheDocument();
  });

  it("renders settings page when authenticated", async () => {
    authState.isAuthenticated = true;
    authState.user = {
      id: "1",
      email: "t@t.com",
      role: "USER",
      is_active: true,
    };
    authState.role = Role.USER;

    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Settings Page")).toBeInTheDocument();
  });

  it("renders AccessDeniedOverlay when accessDenied is true", async () => {
    const mockSetAccessDenied = vi.fn();
    vi.mocked(useAuth).mockImplementation(() => ({
      isAuthenticated: true,
      isLoading: false,
      user: authState.user,
      role: authState.role,
      login: vi.fn(),
      logout: vi.fn(),
      hasPermission: vi.fn().mockReturnValue(true),
      accessDenied: true,
      setAccessDenied: mockSetAccessDenied,
      token: "fake",
    }));

    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByText("Access Forbidden")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Dismiss"));
    expect(mockSetAccessDenied).toHaveBeenCalledWith(false);
  });

  it("handles login and logout cycle", async () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByText("Login Page")).toBeInTheDocument();

    // Click login - this updates authState via mockLogin
    fireEvent.click(screen.getByText("Mock Login"));
    expect(mockLogin).toHaveBeenCalledWith("token");

    // Since AppContent is inside App, and we updated authState,
    // but the component won't re-render automatically because authState is not a React state.
    // However, in a real app, AuthProvider would update.
    // In this test, we can just re-render to pick up the new mock values.

    const { rerender } = render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Dashboard Page")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Mock Logout"));
    expect(mockLogout).toHaveBeenCalled();
  });
});
