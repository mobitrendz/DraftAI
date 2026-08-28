import { useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

type ProviderRemoveMode = "custom" | "credentials";

interface DeleteProviderConfirmModalProps {
  providerLabel: string;
  mode: ProviderRemoveMode;
  isDeleting: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

const DeleteProviderConfirmModal = ({
  providerLabel,
  mode,
  isDeleting,
  onClose,
  onConfirm,
}: DeleteProviderConfirmModalProps) => {
  const [confirmation, setConfirmation] = useState("");
  const nameMatches = confirmation.trim() === providerLabel;
  const isCustomRemoval = mode === "custom";

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!nameMatches || isDeleting) {
      return;
    }
    onConfirm();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div
        className="max-w-md w-full rounded-2xl border border-destructive/20 bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-provider-title"
      >
        <div className="flex items-center justify-between gap-3 border-b border-border px-6 py-4">
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="w-5 h-5" />
            <h3 id="delete-provider-title" className="font-semibold text-foreground">
              {isCustomRemoval ? "Remove provider?" : "Remove API key?"}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-muted-foreground hover:text-foreground hover:bg-muted"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-6 py-5">
          <p className="text-sm text-foreground">
            {isCustomRemoval ? (
              <>
                This will permanently remove{" "}
                <span className="font-semibold">{providerLabel}</span> and its discovered
                models. This action cannot be undone.
              </>
            ) : (
              <>
                This will remove the saved API key for{" "}
                <span className="font-semibold">{providerLabel}</span>. You can add a new
                key later if needed.
              </>
            )}
          </p>

          <div className="space-y-2">
            <Label htmlFor="confirm-provider-name">
              Type <span className="font-semibold">{providerLabel}</span> to confirm
            </Label>
            <Input
              id="confirm-provider-name"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              placeholder={providerLabel}
              autoFocus
              autoComplete="off"
            />
            {confirmation.length > 0 && !nameMatches && (
              <p className="text-xs text-destructive">Provider name does not match.</p>
            )}
          </div>

          <div className="flex gap-3 pt-2">
            <Button type="button" variant="outline" className="flex-1" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="destructive"
              className="flex-1"
              disabled={!nameMatches || isDeleting}
            >
              {isDeleting
                ? "Removing..."
                : isCustomRemoval
                  ? "Remove provider"
                  : "Remove API key"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DeleteProviderConfirmModal;
