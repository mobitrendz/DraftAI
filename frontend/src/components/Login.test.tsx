import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Login from "./Login";
import {
  loginAccessTokenApiV1LoginAccessTokenPost,
  registerUserApiV1LoginSignupPost,
} from "../client";
import { useAuth } from "../contexts/AuthContext";

// Mock the SDK and auth
vi.mock("../client", () => ({
  loginAccessTokenApiV1LoginAccessTokenPost: vi.fn(),
  registerUserApiV1LoginSignupPost: vi.fn(),
}));

vi.mock("../lib/auth", () => ({
  auth: {
    setToken: vi.fn(),
    clearToken: vi.fn(),
    getToken: vi.fn(),
    isAuthenticated: vi.fn(),
    initialize: vi.fn(),
  },
}));

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  Role: {
    SUPER: "SUPER",
    ADMIN: "ADMIN",
    USER: "USER",
  },
  AuthProvider: ({ children }: any) => <div>{children}</div>,
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

describe("Login Component", () => {
  const mockLogin = vi.fn();
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
    vi.mocked(useAuth).mockReturnValue({
      login: mockLogin,
      logout: vi.fn(),
      user: null,
      role: null,
      isAuthenticated: false,
      isLoading: false,
      accessDenied: false,
      setAccessDenied: vi.fn(),
      hasPermission: vi.fn(),
      token: null,
    });
    window.alert = vi.fn();
  });

  const renderLogin = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      </QueryClientProvider>,
    );

  it("handles successful login", async () => {
    vi.mocked(loginAccessTokenApiV1LoginAccessTokenPost).mockResolvedValue({
      data: { access_token: "fake-token" },
    } as any);

    renderLogin();

    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign In/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("fake-token");
    });
  });

  it("handles generic login failure", async () => {
    renderLogin();
    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: "any@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "any" },
    });

    vi.mocked(loginAccessTokenApiV1LoginAccessTokenPost).mockResolvedValueOnce({
      error: { detail: "Invalid credentials" },
    } as any);
    fireEvent.click(screen.getByRole("button", { name: /Sign In/i }));
    expect(await screen.findByText(/Invalid credentials/i)).toBeInTheDocument();
  });

  it("handles inactive user account failure", async () => {
    renderLogin();
    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: "any@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "any" },
    });

    vi.mocked(loginAccessTokenApiV1LoginAccessTokenPost).mockResolvedValueOnce({
      error: { detail: "Inactive user" },
    } as any);
    fireEvent.click(screen.getByRole("button", { name: /Sign In/i }));
    expect(
      await screen.findByText(/Your account is currently inactive/i),
    ).toBeInTheDocument();
  });

  it("handles signup workflow and errors", async () => {
    renderLogin();

    // 1. Success path
    vi.mocked(registerUserApiV1LoginSignupPost).mockResolvedValueOnce({
      data: {},
    } as any);
    fireEvent.click(screen.getByText(/Don't have an account\? Sign up/i));

    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: "new@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "pass123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Create Account/i }));

    await waitFor(() => {
      expect(registerUserApiV1LoginSignupPost).toHaveBeenCalled();
      expect(window.alert).toHaveBeenCalledWith(
        "Signup successful! Please sign in.",
      );
    });

    // 2. Error path
    // Switches back to Login mode. Switch to Signup again.
    fireEvent.click(
      await screen.findByText(/Don't have an account\? Sign up/i),
    );

    vi.mocked(registerUserApiV1LoginSignupPost).mockResolvedValueOnce({
      error: { detail: "Already exists" },
    } as any);
    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: "exists@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "pass123" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Create Account/i }));
    expect(await screen.findByText(/Already exists/i)).toBeInTheDocument();
  });

  it("handles network errors and fallback messages", async () => {
    renderLogin();

    const submitButton = screen.getByRole("button", { name: /Sign In/i });
    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: "test@test.com" },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: "test" },
    });

    // 1. Network error (catch block handled by TanStack mutation error)
    vi.mocked(loginAccessTokenApiV1LoginAccessTokenPost).mockRejectedValueOnce(
      new Error("Network Error"),
    );
    fireEvent.click(submitButton);
    expect(await screen.findByText(/Network Error/i)).toBeInTheDocument();

    // 2. Array detail error
    vi.mocked(loginAccessTokenApiV1LoginAccessTokenPost).mockResolvedValueOnce({
      error: { detail: [{ msg: "Error 1" }, { msg: "Error 2" }] },
    } as any);
    fireEvent.click(submitButton);
    expect(
      await screen.findByText(/Error 1; error: Error 2/i),
    ).toBeInTheDocument();
  });
});
