import { AlertTriangle, X } from "lucide-react";
import { Button } from "./ui/button";

interface DeleteDraftConfirmModalProps {
  topic: string;
  isDeleting: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

const DeleteDraftConfirmModal = ({
  topic,
  isDeleting,
  onClose,
  onConfirm,
}: DeleteDraftConfirmModalProps) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div
        className="max-w-md w-full rounded-2xl border border-destructive/20 bg-card shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-draft-title"
      >
        <div className="flex items-center justify-between gap-3 border-b border-border px-6 py-4">
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="w-5 h-5" />
            <h3 id="delete-draft-title" className="font-semibold text-foreground">
              Delete draft?
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

        <div className="space-y-4 px-6 py-5">
          <p className="text-sm text-foreground">
            This will permanently delete{" "}
            <span className="font-semibold">{topic}</span> and all associated content:
          </p>
          <ul className="text-sm text-muted-foreground list-disc pl-5 space-y-1">
            <li>DEV.to article</li>
            <li>LinkedIn post</li>
            <li>Cover images</li>
          </ul>
          <p className="text-sm text-muted-foreground">This action cannot be undone.</p>

          <div className="flex gap-3 pt-2">
            <Button type="button" variant="outline" className="flex-1" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              className="flex-1"
              disabled={isDeleting}
              onClick={onConfirm}
            >
              {isDeleting ? "Deleting..." : "Delete draft"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeleteDraftConfirmModal;
