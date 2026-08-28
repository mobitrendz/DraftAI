import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminActivityDashboard from "./AdminActivityDashboard";
import { useAuth, Role } from "../../../contexts/AuthContext";
import * as sdk from "../../../client/sdk.gen";

vi.mock("../../../contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  Role: {
    SUPER: "SUPER",
    ADMIN: "ADMIN",
    USER: "USER",
  },
}));

vi.mock("../../../client/sdk.gen", () => ({
  readAllActivitiesApiV1ActivitiesGet: vi.fn(),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

describe("AdminActivityDashboard", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
  });

  const renderDashboard = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AdminActivityDashboard />
      </QueryClientProvider>,
    );

  it("renders access restricted for non-admin users", () => {
    vi.mocked(useAuth).mockReturnValue({
      role: Role.USER,
      token: "fake-token",
      hasPermission: (r: Role) => r === Role.USER,
    } as any);

    renderDashboard();
    expect(screen.getByText(/Access Restricted/i)).toBeInTheDocument();
  });

  it("fetches and displays activity for admin users", async () => {
    vi.mocked(sdk.readAllActivitiesApiV1ActivitiesGet).mockResolvedValueOnce({
      data: {
        items: [
          {
            id: "act-1",
            user_id: "user-1234",
            method: "GET",
            path: "/api/v1/users",
            status_code: 200,
            ip_address: "127.0.0.1",
            created_at: "2026-06-15T12:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        size: 50,
        pages: 1,
      },
      error: null,
    } as any);

    vi.mocked(useAuth).mockReturnValue({
      role: Role.ADMIN,
      token: "fake-token",
      hasPermission: (r: Role) => r === Role.ADMIN || r === Role.USER,
    } as any);

    renderDashboard();

    await waitFor(() =>
      expect(screen.getByText(/GET \/api\/v1\/users/i)).toBeInTheDocument(),
    );
    expect(screen.getByText("Platform Activity")).toBeInTheDocument();
  });
});
