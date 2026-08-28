import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminDashboardView from "./AdminDashboardView";
import * as sdk from "../../client/sdk.gen";
import { useAuth, Role } from "../../contexts/AuthContext";

vi.mock("../../client/sdk.gen", () => ({
  updateUserApiV1UsersIdPatch: vi.fn(),
  deleteUserApiV1UsersIdDelete: vi.fn(),
  createUserApiV1UsersPost: vi.fn(),
}));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  Role: {
    SUPER: "SUPER",
    ADMIN: "ADMIN",
    USER: "USER",
  },
}));

vi.mock("./AdminUserTable", () => ({
  default: ({ onToggleStatus, onDeleteUser }: any) => (
    <div data-testid="admin-user-table">
      <button onClick={() => onToggleStatus({ id: "1", is_active: false })}>
        Toggle User
      </button>
      <button onClick={() => onDeleteUser({ id: "2" })}>Delete User</button>
    </div>
  ),
}));
vi.mock("./CreateAdminForm", () => ({
  default: ({ onSubmit, onClose }: any) => (
    <div data-testid="create-admin-form">
      <form onSubmit={onSubmit} aria-label="create-form">
        <button type="submit">Submit Form</button>
      </form>
      <button onClick={onClose}>Close Form</button>
    </div>
  ),
}));
vi.mock("./DeleteUserConfirmModal", () => ({
  default: ({ onConfirm, onClose }: any) => (
    <div data-testid="delete-confirm-modal">
      <button onClick={onConfirm}>Confirm Delete</button>
      <button onClick={onClose}>Cancel Delete</button>
    </div>
  ),
}));
vi.mock("./activity/AdminActivityDashboard", () => ({
  default: () => <div data-testid="admin-activity-dashboard" />,
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

describe("AdminDashboardView", () => {
  const mockCurrentUser = {
    id: "admin-1",
    email: "admin@test.com",
    role: "admin",
    is_active: true,
  } as any;

  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as any).mockReturnValue({
      role: Role.SUPER,
      user: mockCurrentUser,
    });
    queryClient = createTestQueryClient();
  });

  const renderView = (props = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminDashboardView currentUser={mockCurrentUser} {...props} />
        </MemoryRouter>
      </QueryClientProvider>,
    );
  };

  it("renders activity tab by default for SUPER role", () => {
    renderView();
    expect(screen.getByText("Super User Control Center")).toBeInTheDocument();
    expect(screen.getByTestId("admin-activity-dashboard")).toBeInTheDocument();
  });

  it("renders Identity & Access for ADMIN role", () => {
    (useAuth as any).mockReturnValue({
      role: Role.ADMIN,
      user: mockCurrentUser,
    });
    renderView();
    expect(screen.getByText("Identity & Access")).toBeInTheDocument();
    expect(screen.getByTestId("admin-activity-dashboard")).toBeInTheDocument();
  });

  it("switches tabs correctly", () => {
    renderView();
    fireEvent.click(screen.getByText("Users"));
    expect(screen.getByTestId("admin-user-table")).toBeInTheDocument();
  });

  it("opens CreateAdminForm and creates a user", async () => {
    (sdk.createUserApiV1UsersPost as any).mockResolvedValue({});
    renderView({ initialTab: "users" });
    fireEvent.click(screen.getByText("Provision Admin"));
    fireEvent.submit(screen.getByRole("form", { name: "create-form" }));

    await waitFor(() => {
      expect(sdk.createUserApiV1UsersPost).toHaveBeenCalled();
      expect(screen.queryByTestId("create-admin-form")).not.toBeInTheDocument();
    });
  });
});
