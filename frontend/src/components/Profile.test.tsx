import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Profile from "./Profile";
import * as sdk from "../client/sdk.gen";
import { useAuth, Role } from "../contexts/AuthContext";

// Mock the entire SDK
vi.mock("../client/sdk.gen", () => ({
  getCurrentUserApiV1LoginCurrentUserGet: vi.fn(() =>
    Promise.resolve({ data: {} }),
  ),
  updateUserApiV1UsersIdPatch: vi.fn(() => Promise.resolve({ data: {} })),
  deleteUserApiV1UsersIdDelete: vi.fn(() => Promise.resolve({ data: {} })),
  loginAccessTokenApiV1LoginAccessTokenPost: vi.fn(() =>
    Promise.resolve({ data: {} }),
  ),
  updatePasswordApiV1UsersPasswordPatch: vi.fn(() =>
    Promise.resolve({ data: {} }),
  ),
}));

vi.mock("../lib/auth", () => ({
  auth: {
    initialize: vi.fn(),
    isAuthenticated: vi.fn(),
    clearToken: vi.fn(),
    getToken: vi.fn(),
    setToken: vi.fn(),
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

describe("Profile Component", () => {
  const mockUser = {
    id: "user-123",
    email: "john@example.com",
    full_name: "John Doe",
    role: "user",
    is_active: true,
  };
  const mockLogout = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuth).mockReturnValue({
      user: mockUser as any,
      role: Role.USER,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: mockLogout,
      hasPermission: vi.fn((r) => r === Role.USER),
      accessDenied: false,
      setAccessDenied: vi.fn(),
      token: "fake-token",
    });
    vi.mocked(sdk.getCurrentUserApiV1LoginCurrentUserGet).mockResolvedValue({
      data: mockUser,
    } as any);
    window.alert = vi.fn();
    window.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("handles profile update", async () => {
    vi.mocked(sdk.updateUserApiV1UsersIdPatch).mockResolvedValue({
      data: { ...mockUser, full_name: "John Updated" },
    } as any);
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByText(/Edit Profile/i));
    const nameInput = await screen.findByLabelText(/Full Name/i);
    fireEvent.change(nameInput, { target: { value: "John Updated" } });
    fireEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    await waitFor(() => {
      expect(screen.getByText("John Updated")).toBeInTheDocument();
    });
  });

  it("handles password validation mismatch", async () => {
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByText("Change Password"));

    const currentPassInput = await screen.findByLabelText(/Current Password/i);
    const newPassInput = screen.getByLabelText(/^New Password$/i);
    const confirmPassInput = screen.getByLabelText(/Confirm New Password/i);

    fireEvent.change(currentPassInput, { target: { value: "any" } });
    fireEvent.change(newPassInput, { target: { value: "p1" } });
    fireEvent.change(confirmPassInput, { target: { value: "p2" } });

    fireEvent.click(screen.getByRole("button", { name: /^Update Password$/i }));
    expect(
      await screen.findByText(/New passwords do not match/i),
    ).toBeInTheDocument();
  });

  it("handles successful password update", async () => {
    vi.mocked(sdk.updatePasswordApiV1UsersPasswordPatch).mockResolvedValue({
      data: {},
    } as any);
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByText("Change Password"));

    fireEvent.change(await screen.findByLabelText(/Current Password/i), {
      target: { value: "oldpass" },
    });
    fireEvent.change(screen.getByLabelText(/^New Password$/i), {
      target: { value: "newpass" },
    });
    fireEvent.change(screen.getByLabelText(/Confirm New Password/i), {
      target: { value: "newpass" },
    });

    fireEvent.click(screen.getByRole("button", { name: /^Update Password$/i }));

    // Check success message appears
    expect(
      await screen.findByText(/Password successfully updated!/i),
    ).toBeInTheDocument();

    // Check it disappears after 2 seconds
    await waitFor(
      () => {
        expect(
          screen.queryByText(/Password successfully updated!/i),
        ).not.toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });

  it("handles deletion process", async () => {
    vi.mocked(sdk.loginAccessTokenApiV1LoginAccessTokenPost).mockResolvedValue({
      data: { access_token: "v" },
    } as any);
    vi.mocked(sdk.deleteUserApiV1UsersIdDelete).mockResolvedValue({
      data: {},
    } as any);

    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByText(/Delete My Account/i));

    const confirmInput = await screen.findByLabelText(/Verify Password/i);
    fireEvent.change(confirmInput, { target: { value: "pass" } });
    fireEvent.click(screen.getByRole("button", { name: /Confirm Deletion/i }));

    await waitFor(() => {
      expect(sdk.deleteUserApiV1UsersIdDelete).toHaveBeenCalled();
      expect(mockLogout).toHaveBeenCalled();
    });
  });

  it("handles password update failure", async () => {
    vi.mocked(sdk.updatePasswordApiV1UsersPasswordPatch).mockRejectedValue({
      detail: "Incorrect password",
    } as any);
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByText("Change Password"));
    fireEvent.change(await screen.findByLabelText(/Current Password/i), {
      target: { value: "wrong" },
    });
    fireEvent.change(screen.getByLabelText(/^New Password$/i), {
      target: { value: "new" },
    });
    fireEvent.change(screen.getByLabelText(/Confirm New Password/i), {
      target: { value: "new" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^Update Password$/i }));

    expect(await screen.findByText(/Incorrect password/i)).toBeInTheDocument();
  });

  it("handles account deletion failure", async () => {
    vi.mocked(sdk.loginAccessTokenApiV1LoginAccessTokenPost).mockResolvedValue({
      data: { access_token: "v" },
    } as any);
    vi.mocked(sdk.deleteUserApiV1UsersIdDelete).mockRejectedValue(
      new Error("API Error"),
    );

    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByText(/Delete My Account/i));
    fireEvent.change(await screen.findByLabelText(/Verify Password/i), {
      target: { value: "pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Confirm Deletion/i }));

    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith(
        expect.stringContaining("error occurred while deleting your account"),
      );
    });
  });

  it("handles cancelling profile edit", async () => {
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByText(/Edit Profile/i));
    fireEvent.click(screen.getByRole("button", { name: /Cancel/i }));
    expect(screen.queryByLabelText(/Full Name/i)).not.toBeInTheDocument();
  });

  it("handles cancelling password change", async () => {
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByText("Change Password"));
    fireEvent.click(screen.getByRole("button", { name: /Cancel/i }));
    expect(
      screen.queryByLabelText(/Current Password/i),
    ).not.toBeInTheDocument();
  });

  it("handles failed password verification for deletion", async () => {
    vi.mocked(sdk.loginAccessTokenApiV1LoginAccessTokenPost).mockRejectedValue({
      detail: "Invalid",
    } as any);
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByText(/Delete My Account/i));
    fireEvent.change(await screen.findByLabelText(/Verify Password/i), {
      target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Confirm Deletion/i }));

    expect(await screen.findByText(/Invalid password/i)).toBeInTheDocument();
  });

  it("handles account protection for super users", async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: { ...mockUser, role: "super" } as any,
      role: Role.SUPER,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      hasPermission: vi.fn((r) => r === Role.SUPER),
      accessDenied: false,
      setAccessDenied: vi.fn(),
      token: "fake-token",
    });

    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/Account Protection/i)).toBeInTheDocument();
    expect(screen.getByText(/Delete My Account \(Disabled\)/i)).toBeDisabled();
    expect(screen.queryByText("Danger Zone")).not.toBeInTheDocument();
  });
});
