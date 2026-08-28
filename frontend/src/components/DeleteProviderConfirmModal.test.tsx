import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import DeleteProviderConfirmModal from "./DeleteProviderConfirmModal";

describe("DeleteProviderConfirmModal", () => {
  const defaultProps = {
    providerLabel: "My LM Studio",
    mode: "custom" as const,
    isDeleting: false,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders provider name and confirmation instructions", () => {
    render(<DeleteProviderConfirmModal {...defaultProps} />);

    expect(screen.getByText("Remove provider?")).toBeInTheDocument();
    expect(screen.getAllByText("My LM Studio").length).toBeGreaterThan(0);
    expect(screen.getByLabelText(/Type My LM Studio to confirm/i)).toBeInTheDocument();
  });

  it("keeps remove disabled until provider name matches", () => {
    render(<DeleteProviderConfirmModal {...defaultProps} />);

    const removeButton = screen.getByRole("button", { name: "Remove provider" });
    expect(removeButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/Type My LM Studio to confirm/i), {
      target: { value: "Wrong Name" },
    });
    expect(removeButton).toBeDisabled();
    expect(screen.getByText("Provider name does not match.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Type My LM Studio to confirm/i), {
      target: { value: "My LM Studio" },
    });
    expect(removeButton).not.toBeDisabled();
  });

  it("calls onConfirm when name matches and form is submitted", () => {
    render(<DeleteProviderConfirmModal {...defaultProps} />);

    fireEvent.change(screen.getByLabelText(/Type My LM Studio to confirm/i), {
      target: { value: "My LM Studio" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Remove provider" }));

    expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when cancel is clicked", () => {
    render(<DeleteProviderConfirmModal {...defaultProps} />);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("disables remove while deletion is in progress", () => {
    render(<DeleteProviderConfirmModal {...defaultProps} isDeleting />);

    expect(screen.getByRole("button", { name: "Removing..." })).toBeDisabled();
  });

  it("shows API key removal copy for built-in providers", () => {
    render(
      <DeleteProviderConfirmModal
        {...defaultProps}
        providerLabel="OpenAI"
        mode="credentials"
      />,
    );

    expect(screen.getByText("Remove API key?")).toBeInTheDocument();
    expect(screen.getByText(/remove the saved API key for/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove API key" })).toBeDisabled();
  });
});
