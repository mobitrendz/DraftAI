import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import React from "react";
import DeleteUserConfirmModal from "./DeleteUserConfirmModal";
import * as sdk from "../../client/sdk.gen";

vi.mock("../../client/sdk.gen", () => ({
  loginAccessTokenApiV1LoginAccessTokenPost: vi.fn(),
}));

describe("DeleteUserConfirmModal", () => {
  const mockUserToDelete = {
    id: "user-1",
    email: "target@test.com",
    role: "user" as any,
  };

  const defaultProps = {
    userToDelete: mockUserToDelete,
    currentUserEmail: "admin@test.com",
    isDeleting: false,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders correctly with target user email", () => {
    render(<DeleteUserConfirmModal {...defaultProps} />);
    expect(screen.getByText("target@test.com")).toBeInTheDocument();
    expect(screen.getByText("Confirm Deletion")).toBeInTheDocument();
  });

  it("calls onClose when cancel button or X is clicked", () => {
    render(<DeleteUserConfirmModal {...defaultProps} />);

    fireEvent.click(screen.getByText("Cancel"));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);

    const xButton = screen.getAllByRole("button")[0];
    fireEvent.click(xButton);
    expect(defaultProps.onClose).toHaveBeenCalledTimes(2);
  });

  it("calls onConfirm if password verification succeeds", async () => {
    (sdk.loginAccessTokenApiV1LoginAccessTokenPost as any).mockResolvedValue({
      data: { access_token: "fake-token" },
    });

    render(<DeleteUserConfirmModal {...defaultProps} />);

    fireEvent.change(
      screen.getByPlaceholderText("Enter your current password"),
      {
        target: { value: "correct-password" },
      },
    );
    fireEvent.submit(screen.getByRole("button", { name: "Confirm Delete" }));

    await waitFor(() => {
      expect(
        sdk.loginAccessTokenApiV1LoginAccessTokenPost,
      ).toHaveBeenCalledWith({
        body: { username: "admin@test.com", password: "correct-password" },
      });
      expect(defaultProps.onConfirm).toHaveBeenCalled();
    });
  });

  it("displays error if password verification fails (no token)", async () => {
    (sdk.loginAccessTokenApiV1LoginAccessTokenPost as any).mockResolvedValue({
      data: null,
    });

    render(<DeleteUserConfirmModal {...defaultProps} />);

    fireEvent.change(
      screen.getByPlaceholderText("Enter your current password"),
      {
        target: { value: "wrong-password" },
      },
    );
    fireEvent.submit(screen.getByRole("button", { name: "Confirm Delete" }));

    await waitFor(() => {
      expect(
        screen.getByText("Incorrect password. Please try again."),
      ).toBeInTheDocument();
      expect(defaultProps.onConfirm).not.toHaveBeenCalled();
    });
  });

  it("displays error if password verification API throws error", async () => {
    (sdk.loginAccessTokenApiV1LoginAccessTokenPost as any).mockRejectedValue(
      new Error("API Error"),
    );

    render(<DeleteUserConfirmModal {...defaultProps} />);

    fireEvent.change(
      screen.getByPlaceholderText("Enter your current password"),
      {
        target: { value: "error-password" },
      },
    );
    fireEvent.submit(screen.getByRole("button", { name: "Confirm Delete" }));

    await waitFor(() => {
      expect(
        screen.getByText("Invalid credentials. Password verification failed."),
      ).toBeInTheDocument();
      expect(defaultProps.onConfirm).not.toHaveBeenCalled();
    });
  });

  it("shows processing state when isDeleting is true", () => {
    render(<DeleteUserConfirmModal {...defaultProps} isDeleting={true} />);
    const submitBtn = screen.getByRole("button", { name: "Processing..." });
    expect(submitBtn).toBeDisabled();
  });
});
