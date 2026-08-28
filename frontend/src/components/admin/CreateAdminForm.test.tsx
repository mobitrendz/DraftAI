import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import React from "react";
import CreateAdminForm from "./CreateAdminForm";

describe("CreateAdminForm", () => {
  const defaultProps = {
    email: "test@example.com",
    fullName: "Test User",
    isSubmitting: false,
    isSuper: false,
    error: null,
    onClose: vi.fn(),
    onSubmit: vi.fn((e) => e.preventDefault()),
    onEmailChange: vi.fn(),
    onPasswordChange: vi.fn(),
    onFullNameChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders correctly for a normal user creation", () => {
    render(<CreateAdminForm {...defaultProps} />);
    expect(screen.getByText("New System User")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Create User Account" }),
    ).toBeInTheDocument();
  });

  it("renders correctly for an admin user creation", () => {
    render(<CreateAdminForm {...defaultProps} isSuper={true} />);
    expect(screen.getByText("New Admin User")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Create Admin Account" }),
    ).toBeInTheDocument();
  });

  it("displays error message if passed", () => {
    render(<CreateAdminForm {...defaultProps} error="Email already exists!" />);
    expect(screen.getByText("Email already exists!")).toBeInTheDocument();
  });

  it("calls input handlers on change", () => {
    render(<CreateAdminForm {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(/Full Name/i), {
      target: { value: "New Name" },
    });
    expect(defaultProps.onFullNameChange).toHaveBeenCalledWith("New Name");

    fireEvent.change(screen.getByLabelText(/Email Address/i), {
      target: { value: "new@test.com" },
    });
    expect(defaultProps.onEmailChange).toHaveBeenCalledWith("new@test.com");

    fireEvent.change(screen.getByLabelText(/Temporary Password/i), {
      target: { value: "password123" },
    });
    expect(defaultProps.onPasswordChange).toHaveBeenCalledWith("password123");
  });

  it("calls onClose when cancel or X is clicked", () => {
    render(<CreateAdminForm {...defaultProps} />);

    fireEvent.click(screen.getByText("Cancel"));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);

    // The X button is the first button without text content or we can find it by looking for the button before form
    const xButton = screen.getAllByRole("button")[0];
    fireEvent.click(xButton);
    expect(defaultProps.onClose).toHaveBeenCalledTimes(2);
  });

  it("disables submit button and shows provisioning when submitting", () => {
    render(<CreateAdminForm {...defaultProps} isSubmitting={true} />);
    const submitBtn = screen.getByRole("button", { name: "Provisioning..." });
    expect(submitBtn).toBeDisabled();
  });
});
