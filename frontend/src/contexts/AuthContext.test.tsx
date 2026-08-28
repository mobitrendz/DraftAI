import { render, screen, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React, { useEffect } from "react";
import { AuthProvider, useAuth, useHasPermission, Role } from "./AuthContext";
import { jwtDecode } from "jwt-decode";
import { auth } from "../lib/auth";
import { client } from "../client/client.gen";
import * as sdk from "../client/sdk.gen";

vi.mock("../lib/auth", () => ({
  auth: {
    initialize: vi.fn(),
    getToken: vi.fn(),
    setToken: vi.fn(),
    clearToken: vi.fn(),
  },
}));

vi.mock("../client/sdk.gen", () => ({
  getCurrentUserApiV1LoginCurrentUserGet: vi.fn(),
}));

vi.mock("jwt-decode", () => ({
  jwtDecode: vi.fn((token) => {
    if (token === "bad-token") throw new Error("Invalid token");
    return {
      sub: "test-user-id",
      email: "test@example.com",
      full_name: "Test User",
      role: "ADMIN",
    };
  }),
}));

vi.mock("../client/client.gen", () => ({
  client: {
    interceptors: {
      request: {
        use: vi.fn(),
        eject: vi.fn(),
      },
      response: {
        use: vi.fn(),
        eject: vi.fn(),
      },
      error: {
        use: vi.fn(),
        eject: vi.fn(),
      },
    },
  },
}));

const TestComponent = () => {
  const {
    user,
    token,
    role,
    isAuthenticated,
    isLoading,
    accessDenied,
    login,
    logout,
    hasPermission,
  } = useAuth();

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <div data-testid="auth-status">
        {isAuthenticated ? "Authenticated" : "Not Authenticated"}
      </div>
      <div data-testid="user-role">{role || "No Role"}</div>
      <div data-testid="access-denied">
        {accessDenied ? "Denied" : "Allowed"}
      </div>
      <div data-testid="has-super">
        {hasPermission(Role.SUPER) ? "Yes" : "No"}
      </div>
      <div data-testid="has-admin">
        {hasPermission(Role.ADMIN) ? "Yes" : "No"}
      </div>
      <div data-testid="has-user">
        {hasPermission(Role.USER) ? "Yes" : "No"}
      </div>
      <button onClick={() => login("fake-token")}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (auth.getToken as any).mockReturnValue(null);
  });

  it("provides initial unauthenticated state", async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
    });

    expect(screen.getByTestId("auth-status")).toHaveTextContent(
      "Not Authenticated",
    );
    expect(screen.getByTestId("user-role")).toHaveTextContent("No Role");
  });

  it("logs in user and fetches profile via API", async () => {
    (sdk.getCurrentUserApiV1LoginCurrentUserGet as any).mockResolvedValue({
      data: {
        id: "123",
        email: "test@example.com",
        full_name: "API User",
        role: "ADMIN",
        is_active: true,
      },
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );

    act(() => {
      screen.getByText("Login").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "Authenticated",
      );
      expect(screen.getByTestId("user-role")).toHaveTextContent("ADMIN");
      expect(screen.getByTestId("has-super")).toHaveTextContent("No");
      expect(screen.getByTestId("has-admin")).toHaveTextContent("Yes");
      expect(screen.getByTestId("has-user")).toHaveTextContent("Yes");
    });
  });

  it("logs in user and falls back to JWT if API fails", async () => {
    (sdk.getCurrentUserApiV1LoginCurrentUserGet as any).mockRejectedValue(
      new Error("API Error"),
    );

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(screen.queryByText("Loading...")).not.toBeInTheDocument(),
    );

    act(() => {
      screen.getByText("Login").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "Authenticated",
      );
      expect(screen.getByTestId("user-role")).toHaveTextContent("ADMIN"); // From mocked jwtDecode
    });
  });

  it("logs out user", async () => {
    (auth.getToken as any).mockReturnValue("existing-token");
    (sdk.getCurrentUserApiV1LoginCurrentUserGet as any).mockResolvedValue({
      data: { role: "USER" },
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "Authenticated",
      );
    });

    act(() => {
      screen.getByText("Logout").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "Not Authenticated",
      );
    });
  });

  describe("useAuth hook error", () => {
    it("throws error if used outside AuthProvider", () => {
      // Suppress console.error for expected react error boundary issues in the test
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});
      const TestComponent = () => {
        useAuth();
        return null;
      };

      expect(() => render(<TestComponent />)).toThrow(
        "useAuth must be used within an AuthProvider",
      );
      consoleSpy.mockRestore();
    });
  });

  describe("useHasPermission hook", () => {
    it("returns correct permission boolean", async () => {
      vi.mocked(jwtDecode).mockReturnValue({
        sub: "user-1",
        email: "admin@test.com",
        role: "ADMIN",
      } as any);

      auth.getToken = vi.fn().mockReturnValue("valid-token");
      (sdk.getCurrentUserApiV1LoginCurrentUserGet as any).mockResolvedValue({
        data: {
          id: "user-1",
          email: "admin@test.com",
          role: "admin",
          is_active: true,
        },
      });

      const TestComponent = () => {
        const hasSuper = useHasPermission(Role.SUPER);
        const hasAdmin = useHasPermission(Role.ADMIN);
        const hasUser = useHasPermission(Role.USER);

        return (
          <div>
            <span data-testid="super">{hasSuper ? "yes" : "no"}</span>
            <span data-testid="admin">{hasAdmin ? "yes" : "no"}</span>
            <span data-testid="user">{hasUser ? "yes" : "no"}</span>
          </div>
        );
      };

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("super").textContent).toBe("no");
        expect(screen.getByTestId("admin").textContent).toBe("yes");
        expect(screen.getByTestId("user").textContent).toBe("yes");
      });
    });
  });

  describe("Edge cases and Error handling", () => {
    it("sets accessDenied to true on 403 status", async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>,
      );

      // Trigger the interceptor by calling a mock that simulates a 403 response
      // We need to access the client interceptor or just simulate a response that passes through it
      const [onSuccess] = (client.interceptors.response.use as any).mock
        .calls[0];

      act(() => {
        onSuccess({ status: 403 });
      });

      expect(screen.getByTestId("access-denied")).toHaveTextContent("Denied");
    });

    it("logs out user on 401 status", async () => {
      (auth.getToken as any).mockReturnValue("valid-token");
      (sdk.getCurrentUserApiV1LoginCurrentUserGet as any).mockResolvedValue({
        data: { role: "USER" },
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("auth-status")).toHaveTextContent(
          "Authenticated",
        );
      });

      const [onError] = (client.interceptors.error.use as any).mock.calls[0];

      act(() => {
        onError(new Error("Unauthorized"), { status: 401 });
      });

      expect(screen.getByTestId("auth-status")).toHaveTextContent(
        "Not Authenticated",
      );
      expect(auth.clearToken).toHaveBeenCalled();
    });

    it("logs out on auth initialization error", async () => {
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});
      vi.mocked(jwtDecode).mockImplementationOnce(() => {
        throw new Error("Decode Error");
      });
      (sdk.getCurrentUserApiV1LoginCurrentUserGet as any).mockRejectedValueOnce(
        new Error("Fetch Error"),
      );
      auth.getToken = vi.fn().mockReturnValue("bad-token");

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>,
      );

      await waitFor(() => {
        expect(auth.clearToken).toHaveBeenCalled();
      });
      consoleSpy.mockRestore();
    });

    it("returns false in fetchProfile when data is missing", async () => {
      (sdk.getCurrentUserApiV1LoginCurrentUserGet as any).mockResolvedValueOnce(
        {
          data: null,
        },
      );

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>,
      );

      act(() => {
        screen.getByText("Login").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("auth-status")).toHaveTextContent(
          "Authenticated",
        );
      });
    });

    it("handles missing role in profile (defaults to USER)", async () => {
      (sdk.getCurrentUserApiV1LoginCurrentUserGet as any).mockResolvedValueOnce(
        {
          data: { id: "123", email: "test@test.com" }, // No role
        },
      );

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>,
      );

      act(() => {
        screen.getByText("Login").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("user-role")).toHaveTextContent("USER");
      });
    });

    it("handles alternate role key in JWT (user_role)", async () => {
      (sdk.getCurrentUserApiV1LoginCurrentUserGet as any).mockRejectedValueOnce(
        new Error("API Down"),
      );
      vi.mocked(jwtDecode).mockReturnValueOnce({
        sub: "user-1",
        email: "test@test.com",
        user_role: "SUPER", // Using user_role instead of role
      } as any);

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>,
      );

      act(() => {
        screen.getByText("Login").click();
      });

      await waitFor(() => {
        expect(screen.getByTestId("user-role")).toHaveTextContent("SUPER");
      });
    });
  });
});
