import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AdminUserTable from "./AdminUserTable";
import * as sdk from "../../client/sdk.gen";
import { useAuth, Role } from "../../contexts/AuthContext";

vi.mock("../../client/sdk.gen", () => ({
  readUsersApiV1UsersGet: vi.fn(),
}));

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  Role: {
    SUPER: "SUPER",
    ADMIN: "ADMIN",
    USER: "USER",
  },
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

describe("AdminUserTable", () => {
  const mockCurrentUser = {
    id: "admin-1",
    email: "admin@test.com",
    role: "ADMIN",
  } as any;

  const mockUsers = [
    {
      id: "admin-1",
      email: "admin@test.com",
      full_name: "Admin User",
      role: "admin",
      is_active: true,
      created_at: "2023-01-01T00:00:00Z",
    },
    {
      id: "user-2",
      email: "user2@test.com",
      full_name: "Regular User",
      role: "user",
      is_active: false,
      created_at: "2023-01-02T00:00:00Z",
    },
    {
      id: "super-3",
      email: "super@test.com",
      full_name: "Super User",
      role: "super",
      is_active: true,
      created_at: "2023-01-03T00:00:00Z",
    },
    {
      id: "admin-4",
      email: "admin4@test.com",
      full_name: "Other Admin",
      role: "admin",
      is_active: true,
      created_at: "2023-01-04T00:00:00Z",
    },
  ];

  const mockOnToggleStatus = vi.fn();
  const mockOnDeleteUser = vi.fn();
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
    (useAuth as any).mockReturnValue({
      role: Role.SUPER,
    });
    (sdk.readUsersApiV1UsersGet as any).mockResolvedValue({
      data: { data: mockUsers, count: 15 },
    });
  });

  const renderTable = (props = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <AdminUserTable
          currentUser={mockCurrentUser}
          onToggleStatus={mockOnToggleStatus}
          onDeleteUser={mockOnDeleteUser}
          {...props}
        />
      </QueryClientProvider>,
    );
  };

  it("fetches and renders users correctly", async () => {
    renderTable();

    await waitFor(() => {
      // It shouldn't render "admin-1" (themselves)
      expect(screen.queryByText("admin@test.com")).not.toBeInTheDocument();
      // It should render Regular User and Super User since current user role in test is SUPER
      expect(screen.getByText("Regular User")).toBeInTheDocument();
      expect(screen.getByText("Super User")).toBeInTheDocument();
    });

    // Pagination info (count is 15)
    expect(screen.getByText(/Records/i)).toHaveTextContent(/of 15 Records/);
  });

  it("filters users by search term", async () => {
    renderTable();
    await waitFor(() =>
      expect(screen.getByText("Regular User")).toBeInTheDocument(),
    );

    const searchInput = screen.getByPlaceholderText(
      "Search by name or email...",
    );
    fireEvent.change(searchInput, { target: { value: "super" } });

    expect(screen.getByText("Super User")).toBeInTheDocument();
    expect(screen.queryByText("Regular User")).not.toBeInTheDocument();
  });

  it("filters users by role", async () => {
    renderTable();
    await waitFor(() =>
      expect(screen.getByText("Regular User")).toBeInTheDocument(),
    );

    const select = screen.getByTestId("role-filter");
    fireEvent.change(select, { target: { value: "user" } });

    expect(screen.getByText("Regular User")).toBeInTheDocument();
    expect(screen.queryByText("Super User")).not.toBeInTheDocument();
  });

  it("ADMIN cannot see SUPER users", async () => {
    (useAuth as any).mockReturnValue({
      role: Role.ADMIN,
    });
    renderTable();

    await waitFor(() => {
      expect(screen.getByText("Regular User")).toBeInTheDocument();
      expect(screen.queryByText("Super User")).not.toBeInTheDocument();
    });
  });

  it("calls toggle status for valid user", async () => {
    renderTable();
    await waitFor(() =>
      expect(screen.getByText("Regular User")).toBeInTheDocument(),
    );

    // Toggle status button has text Active or Inactive
    // For manageable users, it's now a select
    const row = screen.getByText("Regular User").closest("tr");
    const statusSelect = row?.querySelector("select");
    if (statusSelect) {
      fireEvent.change(statusSelect, { target: { value: "active" } });
    }

    expect(mockOnToggleStatus).toHaveBeenCalled();
  });

  it("calls delete for valid user", async () => {
    renderTable();
    await waitFor(() =>
      expect(screen.getByText("Regular User")).toBeInTheDocument(),
    );

    // Delete buttons have title="Delete User"
    const deleteBtns = screen
      .getAllByRole("button")
      .filter((b) =>
        b.querySelector("svg")?.classList.contains("lucide-user-minus"),
      );
    // Actually I used UserMinus icon. Let's find by button with icon.
    // In the new UI, the delete button is a ghost button with UserMinus icon.
    // I didn't add title anymore. I should check how to find it.
    // The button has UserMinus icon.

    const deleteBtn = screen
      .getAllByRole("button")
      .find((b) => b.innerHTML.includes("user-minus"));
    if (deleteBtn) fireEvent.click(deleteBtn);

    expect(mockOnDeleteUser).toHaveBeenCalled();
  });

  it("handles fetch users failure", async () => {
    (sdk.readUsersApiV1UsersGet as any).mockResolvedValueOnce({
      error: { detail: "Fetch failed" },
    });

    renderTable();

    await waitFor(() => {
      expect(screen.getByText(/No users found/i)).toBeInTheDocument();
    });
  });

  it("prevents ADMIN from managing other ADMINs", async () => {
    // Current user is ADMIN
    (useAuth as any).mockReturnValue({
      role: Role.ADMIN,
    });

    renderTable();

    await waitFor(() => {
      expect(screen.getByText("Other Admin")).toBeInTheDocument();
    });

    // For "Other Admin", the actions should be disabled or not present.
    const row = screen.getByText("Other Admin").closest("tr");
    const buttons = row?.querySelectorAll("button");

    buttons?.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });

  it("sorts users by name, date, role and status", async () => {
    renderTable();
    await waitFor(() =>
      expect(screen.getByText("Regular User")).toBeInTheDocument(),
    );

    const nameHeader = screen.getByText("User Details");
    const dateHeader = screen.getByText("Registration");
    const roleHeader = screen.getByText("Security Role");
    const statusHeader = screen.getByText("System Status");

    // Default sort is created_at desc
    let rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("Other Admin");

    // Sort by name asc
    fireEvent.click(nameHeader);
    rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("Other Admin");

    // Sort by role asc
    fireEvent.click(roleHeader);
    rows = screen.getAllByRole("row").slice(1);
    // ADMIN < SUPER < USER
    expect(rows[0]).toHaveTextContent("Other Admin");

    // Sort by status desc
    fireEvent.click(statusHeader); // Toggle to asc
    fireEvent.click(statusHeader); // Toggle to desc
    rows = screen.getAllByRole("row").slice(1);
    // Inactive is 0, Active is 1. Desc should show Active first.
    // Super User and Other Admin are active in mock.
    // Regular User is inactive.
    expect(rows[0]).toHaveTextContent("Super User");

    // Sort by date asc
    fireEvent.click(dateHeader);
    rows = screen.getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("Regular User");
  });
});
